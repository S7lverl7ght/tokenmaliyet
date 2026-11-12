from __future__ import annotations

import re
from datetime import date, datetime, timezone
from decimal import Decimal

from .base import BaseCollector, ParsedPrice, RawItem, RawSnapshot, fetch_html, hash_payload

MODEL_HEADER = re.compile(r"^##\s+(Gemini [^\n{]+?)\s*\{\%", re.MULTILINE)
TABLE_BLOCK = re.compile(r"\{\% table \%\}(.*?)\{\% /table \%\}", re.S)
SEPARATOR = re.compile(r"\n\s*---\s*\n")
DATE_PRICE = re.compile(
    r"\$\s?([0-9][0-9,]*\.?[0-9]*)\s*(through|starting)\s+([A-Z][a-z]+)\s+(\d{1,2}),\s*(\d{4})"
)

DIM_LABELS = [
    ("input price", "input", "USD/1M_tokens"),
    ("output price", "output", "USD/1M_tokens"),
    ("context caching price", "cache_read", "USD/1M_tokens"),
    ("caching price", "cache_read", "USD/1M_tokens"),
    ("cache storage", "cache_storage", "USD/1M_tokens"),
    ("audio input", "audio_input", "USD/1M_tokens"),
    ("audio output", "audio_output", "USD/1M_tokens"),
    ("image", "image_input", "USD/image"),
    ("video", "video_input", "USD/second"),
    ("grounding", "request", "USD/1K_requests"),
]
MONTHS = {m: i for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July", "August",
     "September", "October", "November", "December"], start=1)}


def _slug(name: str) -> str:
    s = name.strip().lower().replace(" ", "-").replace("_", "-")
    return re.sub(r"[^a-z0-9.\-]", "", s)


class GeminiCollector(BaseCollector):
    slug = "gemini"
    source_url = "https://ai.google.dev/gemini-api/docs/pricing"
    source_label = "Gemini API Pricing Docs"
    source_type = "official_doc"
    retrieval_method = "http_html"

    def fetch(self) -> RawSnapshot:
        html, final_url = fetch_html(self.source_url)
        text = self._readable(html)
        items: list[RawItem] = []
        headers = list(MODEL_HEADER.finditer(text))
        for idx, header in enumerate(headers):
            model_name = header.group(1).strip()
            end = headers[idx + 1].start() if idx + 1 < len(headers) else len(text)
            section = text[header.end():end]
            block = TABLE_BLOCK.search(section)
            if not block:
                continue
            # The docs print the canonical API id as a markdown link right after the heading.
            link = re.search(r"\[`([a-z0-9.\-]+)`\]", section)
            model_id = link.group(1) if link else _slug(model_name)
            for group in SEPARATOR.split(block.group(1)):
                lines = [ln.strip() for ln in group.strip().splitlines() if ln.strip()]
                bullets = [ln.lstrip("* ").strip() for ln in lines if ln.startswith("*")]
                if not bullets:
                    continue
                label = bullets[0].lower()
                dimension = next((d for k, d, _u in DIM_LABELS if k in label), None)
                if dimension is None:
                    continue
                unit = next(u for k, d, u in DIM_LABELS if d == dimension and k in label)
                if dimension == "request":
                    # Grounding is billed per 1K grounded prompts; the searched surface is a real dimension.
                    unit = "USD/1K_requests"
                value_text = " ".join(bullets[1:])
                items.append(
                    RawItem(
                        model_id=model_id,
                        display_name=model_name,
                        payload={"dimension": dimension, "unit": unit, "value": value_text,
                                 "label": bullets[0]},
                    )
                )
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

    @staticmethod
    def _readable(html: str) -> str:
        import html as htmlmod

        text = re.sub(r"<script.*?</script>", " ", html, flags=re.S)
        text = re.sub(r"<style.*?</style>", " ", text, flags=re.S)
        text = re.sub(r"<[^>]+>", "\n", text)
        text = htmlmod.unescape(text)
        return re.sub(r"\n{2,}", "\n", text)

    def parse(self, snapshot: RawSnapshot) -> list[ParsedPrice]:
        out: list[ParsedPrice] = []
        for item in snapshot.items:
            value = item.payload["value"]
            dated = DATE_PRICE.findall(value)
            if dated:
                today = datetime.now(timezone.utc).date()
                scheduled_only = any(kind == "starting" for _a, kind, *_ in dated) and not any(
                    kind == "through" for _a, kind, *_ in dated
                )
                for amount_s, kind, month, day, year in dated:
                    try:
                        when = date(int(year), MONTHS[month], int(day))
                    except Exception:  # noqa: BLE001
                        when = None
                    # "starting <date>" is a future price: not in force today, keep it but flag schedule.
                    if scheduled_only and when is not None and when > today:
                        continue
                    label = item.payload["label"]
                    out.append(
                        ParsedPrice(
                            model_id=item.model_id,
                            model_display_name=item.display_name,
                            price_dimension=item.payload["dimension"],
                            amount=Decimal(amount_s.replace(",", "")),
                            currency="USD",
                            billing_unit=item.payload["unit"],
                            # effective_from is the date the price itself applies from; a
                            # "through <date>" clause is an expiry marker, so keep it in the tier.
                            effective_from=None if kind == "through" else when,
                            tier_label=("through-" + when.isoformat()) if kind == "through" and when
                            else ("scheduled-" + when.isoformat()) if when else "current",
                            raw_excerpt={"label": label, "value": value[:200]},
                        )
                    )
                continue
            m = re.search(r"\$\s?([0-9][0-9,]*\.?[0-9]*)", value)
            if not m:
                continue
            if item.payload["dimension"] == "request" and "free" in value.lower():
                # "then $X" after a free allowance is the real metered price; keep that reading.
                pass
            out.append(
                ParsedPrice(
                    model_id=item.model_id,
                    model_display_name=item.display_name,
                    price_dimension=item.payload["dimension"],
                    amount=Decimal(m.group(1).replace(",", "")),
                    currency="USD",
                    billing_unit=item.payload["unit"],
                    tier_label=(item.payload["label"] if item.payload["dimension"] == "request"
                                else "standard"),
                    raw_excerpt={"label": item.payload["label"], "value": value[:200]},
                )
            )
        return out
