from __future__ import annotations

import re
from datetime import datetime, timezone
from decimal import Decimal

from bs4 import BeautifulSoup

from .base import BaseCollector, ParsedPrice, RawItem, RawSnapshot, fetch_html, hash_payload

DIM_BY_LABEL = [
    ("INPUT TOKENS (CACHE HIT)", "cache_read"),
    ("INPUT TOKENS (CACHE MISS)", "input"),
    ("CACHE HIT", "cache_read"),
    ("CACHE MISS", "input"),
    ("OUTPUT TOKENS", "output"),
    ("OUTPUT", "output"),
]
FOOTNOTE = re.compile(r"\s*\(\d+\)\s*$")


def _clean(name: str) -> str:
    return FOOTNOTE.sub("", name).strip().lower()


class DeepSeekCollector(BaseCollector):
    slug = "deepseek"
    source_url = "https://api-docs.deepseek.com/quick_start/pricing"
    source_label = "DeepSeek API Pricing Docs"
    source_type = "official_doc"
    retrieval_method = "http_html"

    def fetch(self) -> RawSnapshot:
        html, final_url = fetch_html(self.source_url)
        soup = BeautifulSoup(html, "html.parser")
        items: list[RawItem] = []
        for table in soup.find_all("table"):
            rows = table.find_all("tr")
            models: list[str] = []
            for row in rows:
                cells = [c.get_text(" ", strip=True) for c in row.find_all(["td", "th"])]
                if cells and cells[0].upper().startswith("MODEL") and len(cells) >= 3:
                    models = [_clean(c) for c in cells[1:] if c and "$" not in c]
                    break
            if not models:
                continue
            current_dim: str | None = None
            for row in rows:
                cells = [c.get_text(" ", strip=True) for c in row.find_all(["td", "th"])]
                values = [c for c in cells if c.startswith("$")]
                if not values:
                    continue
                label = " ".join(c.upper() for c in cells if not c.startswith("$"))
                dimension = next((d for k, d in DIM_BY_LABEL if k in label), None)
                if dimension is not None:
                    current_dim = dimension
                else:
                    # continuation row: "PEAK $x $y" belongs to the previous dimension
                    dimension = current_dim
                if dimension is None:
                    continue
                peak = self._peak(label)
                for idx, value in enumerate(values):
                    if idx >= len(models):
                        break
                    items.append(
                        RawItem(
                            model_id=models[idx],
                            display_name=models[idx],
                            payload={
                                "dimension": dimension,
                                "peak_period": peak,
                                "value": value,
                                "label": f"{dimension} {peak} {value}",
                            },
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
    def _peak(label: str) -> str:
        if "OFF-PEAK" in label or "OFF PEAK" in label:
            return "off_peak"
        if "PEAK" in label:
            return "peak"
        return "standard"

    def parse(self, snapshot: RawSnapshot) -> list[ParsedPrice]:
        out: list[ParsedPrice] = []
        for item in snapshot.items:
            m = re.search(r"([0-9]*\.?[0-9]+)", item.payload["value"].replace(",", ""))
            if not m:
                continue
            out.append(
                ParsedPrice(
                    model_id=item.model_id,
                    model_display_name=item.model_id,
                    price_dimension=item.payload["dimension"],
                    amount=Decimal(m.group(1)),
                    currency="USD",
                    billing_unit="USD/1M_tokens",
                    peak_period=item.payload["peak_period"],
                    raw_excerpt={"label": item.payload["label"]},
                )
            )
        return out
