from __future__ import annotations

import re
from datetime import datetime, timezone
from decimal import Decimal

from bs4 import BeautifulSoup

from .base import BaseCollector, ParsedPrice, RawItem, RawSnapshot, fetch_html, hash_payload

DIM_MAP = {"read": "cache_read", "write": "cache_write", "input": "input", "output": "output"}


def _model_id(name: str) -> str:
    slug = name.strip().lower()
    slug = re.sub(r"[^a-z0-9.]+", "-", slug).strip("-")
    return slug if slug.startswith("claude") else f"claude-{slug}"


def _has_class(node, needle: str) -> bool:
    classes = node.get("class") or []
    return any(needle in c for c in classes)


class AnthropicCollector(BaseCollector):
    slug = "anthropic"
    source_url = "https://www.anthropic.com/pricing"
    source_label = "Anthropic API Pricing Page"
    source_type = "official_doc"
    retrieval_method = "http_html"

    def fetch(self) -> RawSnapshot:
        html, final_url = fetch_html(self.source_url)
        soup = BeautifulSoup(html, "html.parser")
        items: list[RawItem] = []
        for card in soup.find_all("div"):
            if not _has_class(card, "modelCard"):
                continue
            title_node = next((c for c in card.find_all("div") if _has_class(c, "modelTitle")), None)
            if title_node is None:
                continue
            heading = title_node.find(["h2", "h3", "h4"])
            name = (heading or title_node).get_text(" ", strip=True)
            prices = []
            # Anthropic kartlari "priceBlock" (Input / Output / Prompt caching) ve her blogun
            # icinde "priceBreakdown" (Prompts <= 100K / > 100K) icerir. Bu IKINCI seviye
            # baglam dilimidir: ayni kalemin farkli fiyatidir ve KARISTIRILMAMALIDIR.
            # Inceleme raporu (12.11.2026): 0,125 ve 0,625 ayni "standard" etiketiyle
            # iki satir olarak yayinlaniyordu; golden test bunu yakaladi.
            for block in card.find_all("div"):
                if not _has_class(block, "priceBlock"):
                    continue
                label_node = next(
                    (c for c in block.find_all("div")
                     if _has_class(c, "priceLabel") and not _has_class(c, "priceLabelSub")),
                    None,
                )
                block_label = label_node.get_text(" ", strip=True) if label_node is not None else ""

                breakdowns = [b for b in block.find_all("div") if _has_class(b, "priceBreakdown")]
                if not breakdowns:
                    breakdowns = [block]
                for bd in breakdowns:
                    context_label = None
                    for row in bd.find_all("div"):
                        if not _has_class(row, "priceRow"):
                            continue
                        subs = [c for c in row.find_all("p") if _has_class(c, "priceLabelSub")]
                        text = row.get_text(" ", strip=True)
                        m = re.match(
                            r"(Read|Write|Input|Output)\s+\$\s?([0-9][0-9,]*\.?[0-9]*)\s*/\s*(MTok|million tokens)",
                            text,
                        )
                        if m:
                            prices.append({
                                "dimension": DIM_MAP[m.group(1).lower()],
                                "amount": m.group(2),
                                "unit": m.group(3),
                                "tier": context_label or block_label or "standard",
                                "raw": text,
                            })
                        elif subs and "$" not in text:
                            # Dilim basligi: "Prompts <= 100K tokens"
                            context_label = text
            # Bu blokta dilim yoksa blok etiketi tier olur (Input/Output/Prompt caching)
            if prices:
                items.append(RawItem(model_id=_model_id(name), display_name=name, payload={"prices": prices}))
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
            for p in item.payload["prices"]:
                out.append(
                    ParsedPrice(
                        model_id=item.model_id,
                        model_display_name=item.display_name,
                        price_dimension=p["dimension"],
                        amount=Decimal(str(p["amount"]).replace(",", "")),
                        currency="USD",
                        billing_unit="USD/1M_tokens",
                        tier_label=p.get("tier"),
                        raw_excerpt=p,
                    )
                )
        return out
