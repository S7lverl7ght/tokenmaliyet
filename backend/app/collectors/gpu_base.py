"""GPU kiralama fiyati toplayicilari.

Token fiyati toplayicilarindan ayri: birim GPU-saat, kanal da farkli (bulut / pazaryeri).
Her toplayici ham yaniti saklar; normalize + QA ayri adimdir.
"""
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import httpx

from ..config import settings

# GPU ailesi -> VRAM (GB). Kaynak VRAM vermiyorsa bu tablodan tamamlanir.
FAMILY_VRAM = {
    "H100": 80, "H200": 141, "B200": 180, "B300": 288, "GB200": 192, "GB300": 288,
    "A100": 80, "A40": 48, "A10": 24, "L40S": 48, "L40": 48, "A6000": 48,
    "RTX 4090": 24, "RTX 5090": 32, "RTX 3090": 24, "RTX 6000": 96, "RTX PRO 6000": 96,
    "MI300X": 192, "V100": 16, "T4": 16, "L4": 24,
}

# Bilinen model adlarini aileye eslestirir (sira onemli: uzun ad once).
FAMILY_PATTERNS = [
    ("RTX PRO 6000", "RTX PRO 6000"), ("RTX 6000", "RTX 6000"),
    ("RTX 5090", "RTX 5090"), ("RTX 4090", "RTX 4090"), ("RTX 3090", "RTX 3090"),
    ("GB300", "GB300"), ("GB200", "GB200"), ("B300", "B300"), ("B200", "B200"),
    ("H200", "H200"), ("H100", "H100"),
    ("A100", "A100"), ("A40", "A40"), ("A10", "A10"), ("A6000", "A6000"),
    ("L40S", "L40S"), ("L40", "L40"), ("L4", "L4"),
    ("MI300X", "MI300X"), ("V100", "V100"), ("T4", "T4"),
]


def family_of(name: str) -> str:
    upper = name.upper()
    for needle, family in FAMILY_PATTERNS:
        if needle.upper() in upper:
            return family
    return name.strip()[:24]


def vram_of(name: str, fallback: int | None = None) -> int | None:
    m = re.search(r"(\d{2,3})\s*GB", name.upper())
    if m:
        return int(m.group(1))
    if fallback:
        return fallback
    return FAMILY_VRAM.get(family_of(name))


@dataclass
class GpuQuote:
    gpu_model: str
    price_per_hour: Decimal
    currency: str = "USD"
    price_kind: str = "on_demand"
    gpu_count: int = 1
    vram_gb: int | None = None
    region: str | None = None
    min_lease_hours: Decimal | None = None
    notes: str | None = None
    raw: dict | None = None

    def family(self) -> str:
        return family_of(self.gpu_model)


@dataclass
class GpuSnapshot:
    provider_slug: str
    provider_name: str
    website: str
    pricing_url: str
    kind: str
    fetched_at: str
    content_hash: str
    snapshot_path: str
    quotes: list[GpuQuote] = field(default_factory=list)


def _get(url: str, *, json_body: dict | None = None, timeout: float = 30.0) -> tuple[str, str]:
    headers = {"User-Agent": settings.user_agent, "Accept-Language": "en-US,en;q=0.9",
               "Accept": "application/json,text/html;q=0.9"}
    last: Exception | None = None
    for attempt in range(3):
        try:
            with httpx.Client(timeout=timeout, follow_redirects=True) as client:
                if json_body is not None:
                    resp = client.post(url, headers=headers, json=json_body)
                else:
                    resp = client.get(url, headers=headers)
                resp.raise_for_status()
                return resp.text, str(resp.url)
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"fetch failed: {url}: {last}")


def save_snapshot(slug: str, text: str) -> str:
    raw_dir = Path(settings.raw_dir)
    raw_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    path = raw_dir / f"gpu_{slug}_{stamp}.txt"
    path.write_text(text, encoding="utf-8")
    return str(path)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def strip_tags(html: str) -> str:
    body = re.sub(r"<(script|style).*?</\1>", " ", html, flags=re.S)
    body = re.sub(r"<[^>]+>", "\u00b7", body)
    body = re.sub(r"\u00b7+", "\u00b7", body)
    return re.sub(r"\s+", " ", body)
