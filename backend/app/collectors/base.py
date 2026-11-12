from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from pathlib import Path

import httpx

from ..config import settings


@dataclass
class ParsedPrice:
    """One normalized price point extracted from a raw source."""

    model_id: str
    model_display_name: str
    price_dimension: str
    amount: Decimal
    currency: str
    billing_unit: str
    unit_quantity: Decimal = Decimal("1")
    tier_label: str | None = None
    peak_period: str | None = None
    effective_from: date | None = None
    raw_excerpt: dict | None = None

    def normalized_usd_per_1m(self) -> Decimal | None:
        """Convert to a comparable USD per 1M tokens value when the dimension is token based."""
        if self.currency != "USD":
            return None
        if "1M" in self.billing_unit or "1m" in self.billing_unit:
            per = self.amount
        elif self.billing_unit.endswith("/token"):
            per = self.amount * Decimal(1_000_000)
        else:
            return None
        return (per / self.unit_quantity).quantize(Decimal("0.000001"))


@dataclass
class RawItem:
    model_id: str
    display_name: str
    payload: dict


@dataclass
class RawSnapshot:
    source_label: str
    source_url: str
    fetched_at: str
    content_hash: str
    snapshot_path: str
    items: list[RawItem] = field(default_factory=list)
    html: str | None = None
    error: str | None = None


def hash_payload(data: object) -> str:
    blob = json.dumps(data, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def _raw_dir() -> Path:
    path = Path(settings.raw_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _get(url: str, *, timeout: float | None = None) -> httpx.Response:
    headers = {"User-Agent": settings.user_agent, "Accept-Language": "en-US,en;q=0.9"}
    last: Exception | None = None
    for attempt in range(settings.http_retries):
        try:
            with httpx.Client(timeout=timeout or settings.http_timeout, follow_redirects=True) as client:
                resp = client.get(url, headers=headers)
                resp.raise_for_status()
                return resp
        except Exception as exc:  # noqa: BLE001 - retry everything once
            last = exc
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"fetch failed: {url}: {last}")


def fetch_json(url: str) -> tuple[object, str, str]:
    resp = _get(url)
    return resp.json(), resp.text, str(resp.url)


def fetch_html(url: str) -> tuple[str, str]:
    resp = _get(url)
    if resp.encoding is None or resp.encoding.lower() == "iso-8859-1":
        resp.encoding = "utf-8"
    return resp.text, str(resp.url)


class BaseCollector:
    """Collector protocol: fetch -> raw snapshot -> normalized pending observations."""

    slug: str = "base"
    source_url: str = ""
    source_label: str = ""
    source_type: str = "official_doc"
    retrieval_method: str = "http_html"
    sales_channel: str = "direct"

    def fetch(self) -> RawSnapshot:  # pragma: no cover - overridden
        raise NotImplementedError

    def parse(self, snapshot: RawSnapshot) -> list[ParsedPrice]:  # pragma: no cover
        raise NotImplementedError

    # -- helpers -------------------------------------------------------
    def save_raw(self, name: str, text: str) -> str:
        stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
        path = _raw_dir() / f"{self.slug}_{name}_{stamp}.txt"
        path.write_text(text, encoding="utf-8")
        return str(path)

    def collect(self) -> tuple[RawSnapshot, list[ParsedPrice]]:
        snapshot = self.fetch()
        prices = self.parse(snapshot)
        return snapshot, prices
