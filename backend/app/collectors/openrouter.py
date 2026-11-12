from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from .base import BaseCollector, ParsedPrice, RawItem, RawSnapshot, fetch_json, hash_payload


def _money(value: object) -> Decimal | None:
    try:
        d = Decimal(str(value))
    except Exception:  # noqa: BLE001
        return None
    return d if d >= 0 else None


class OpenRouterCollector(BaseCollector):
    """OpenRouter is a marketplace: prices here are channel prices, not first-party model prices."""

    slug = "openrouter"
    source_url = "https://openrouter.ai/api/v1/models"
    source_label = "OpenRouter Models API"
    source_type = "official_api"
    retrieval_method = "http_json"
    sales_channel = "marketplace"

    def fetch(self) -> RawSnapshot:
        data, raw_text, final_url = fetch_json(self.source_url)
        records = (data or {}).get("data", []) if isinstance(data, dict) else []
        items = [
            RawItem(model_id=str(r.get("id")), display_name=str(r.get("name") or r.get("id")), payload=r)
            for r in records
            if r.get("id")
        ]
        path = self.save_raw("models", raw_text)
        return RawSnapshot(
            source_label=self.source_label,
            source_url=final_url,
            fetched_at=datetime.now(timezone.utc).isoformat(),
            content_hash=hash_payload(records),
            snapshot_path=path,
            items=items,
        )

    def parse(self, snapshot: RawSnapshot) -> list[ParsedPrice]:
        out: list[ParsedPrice] = []
        for item in snapshot.items:
            pricing = item.payload.get("pricing") or {}
            for field_name, dimension in (
                ("prompt", "input"),
                ("completion", "output"),
                ("request", "request"),
                ("image", "image_output"),
                ("input_cache_read", "cache_read"),
                ("input_cache_write", "cache_write"),
            ):
                amount = _money(pricing.get(field_name))
                if amount is None:
                    continue
                unit = "USD/request" if dimension == "request" else "USD/image" if dimension.startswith("image") else "USD/token"
                out.append(
                    ParsedPrice(
                        model_id=item.model_id,
                        model_display_name=item.display_name,
                        price_dimension=dimension,
                        amount=amount,
                        currency="USD",
                        billing_unit=unit,
                        raw_excerpt={"field": field_name, "value": str(pricing.get(field_name))},
                    )
                )
        return out
