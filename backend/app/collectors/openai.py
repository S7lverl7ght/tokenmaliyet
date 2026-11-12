from __future__ import annotations

import re
from datetime import datetime, timezone
from decimal import Decimal

from .base import BaseCollector, ParsedPrice, RawItem, RawSnapshot, fetch_html, hash_payload

CARD_RE = re.compile(
    r'\{"name":"([^"]{1,90})","description":"((?:[^"\\]|\\.)*)","pricingGroups":\[(.*?)\],"id":"',
    re.S,
)
GROUP_RE = re.compile(r'"title":"([^"]*)","description":"((?:[^"\\]|\\.)*)"', re.S)
PRICE_RE = re.compile(r"\$\s?([0-9][0-9,]*\.?[0-9]*)")

LABEL_MAP = [
    ("cached input", "cache_read"),
    ("cache read", "cache_read"),
    ("cache write", "cache_write"),
    ("cached output", "cache_write"),
    ("audio input", "audio_input"),
    ("audio output", "audio_output"),
    ("image input", "image_input"),
    ("image output", "image_output"),
    ("input", "input"),
    ("output", "output"),
]


def _slug(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", name.strip().lower())
    return s.strip("-")


class OpenAICollector(BaseCollector):
    """OpenAI publishes its price cards inside the Next.js RSC payload of the pricing page."""

    slug = "openai"
    source_url = "https://openai.com/api/pricing/"
    source_label = "OpenAI API Pricing Page"
    source_type = "official_doc"
    retrieval_method = "http_html"

    def fetch(self) -> RawSnapshot:
        html, final_url = fetch_html(self.source_url)
        marker = html.find("pricingCards")
        window = html[marker: marker + 1_200_000] if marker >= 0 else ""
        decoded = window.replace('\\"', '"').replace("\\n", "\n")
        decoded = re.sub(r"[ \t]*\\+[ \t]*\n", "\n", decoded)  # JSON line continuations
        items: list[RawItem] = []
        seen: set[str] = set()
        for name, blurb, groups in CARD_RE.findall(decoded):
            if name in seen or "pricingGroups" in groups:
                continue
            blocks = [body.replace("\\n", "\n") for _title, body in GROUP_RE.findall(groups)
                      if "{prices." not in body]
            if not blocks:
                continue
            seen.add(name)
            items.append(RawItem(model_id=_slug(name), display_name=name,
                                 payload={"name": name, "blurb": blurb[:120], "blocks": blocks}))
        path = self.save_raw("pricing", html)
        return RawSnapshot(
            source_label=self.source_label,
            source_url=final_url,
            fetched_at=datetime.now(timezone.utc).isoformat(),
            content_hash=hash_payload([i.payload for i in items]),
            snapshot_path=path,
            items=items,
            html=html,
        )

    def parse(self, snapshot: RawSnapshot) -> list[ParsedPrice]:
        out: list[ParsedPrice] = []
        for item in snapshot.items:
            for block in item.payload["blocks"]:
                for dimension, amount, unit in self._parse_block(block):
                    out.append(
                        ParsedPrice(
                            model_id=item.model_id,
                            model_display_name=item.display_name,
                            price_dimension=dimension,
                            amount=amount,
                            currency="USD",
                            billing_unit=unit,
                            raw_excerpt={"name": item.model_id, "block": block[:220]},
                        )
                    )
        return out

    @staticmethod
    def _parse_block(block: str) -> list[tuple[str, Decimal, str]]:
        """Turn 'Input: $10.00 / 1M tokens' style text into (dimension, amount, unit)."""
        results: list[tuple[str, Decimal, str]] = []
        for chunk in re.split(r"\n\s*\n", block.replace("\\", "")):
            text = chunk.strip()
            if not text or "$" not in text:
                continue
            label = text.splitlines()[0].strip().lower().rstrip(":")
            dimension = next((d for k, d in LABEL_MAP if label.startswith(k)), None)
            m = PRICE_RE.search(text)
            if dimension is None or not m:
                continue
            amount = Decimal(m.group(1).replace(",", ""))
            tail = text[m.end():].lower()
            if "per minute" in tail:
                unit = "USD/minute"
            elif "per second" in tail:
                unit = "USD/second"
            elif "1k requests" in tail or "1,000 requests" in tail or "per 1k" in tail:
                unit = "USD/1K_requests"
            elif "per image" in tail or "/ image" in tail:
                unit = "USD/image"
            elif "per request" in tail or "/ request" in tail:
                unit = "USD/request"
            elif "1m tokens" in tail:
                unit = "USD/1M_tokens"
            elif "1k tokens" in tail:
                unit = "USD/1K_tokens"
            elif "million" in tail:
                unit = "USD/1M_tokens"
            else:
                continue
            results.append((dimension, amount, unit))
        return results
