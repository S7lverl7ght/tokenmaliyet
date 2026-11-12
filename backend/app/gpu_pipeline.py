"""GPU fiyatlarini veritabanina yazar (idempotent) ve QA uygular."""
from __future__ import annotations

import datetime as dt
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from .collectors.gpu_base import GpuSnapshot, GpuQuote, family_of
from .models import GpuPrice, GpuProvider


def get_or_create_provider(db: Session, snapshot: GpuSnapshot) -> GpuProvider:
    provider = db.scalar(select(GpuProvider).where(GpuProvider.slug == snapshot.provider_slug))
    if provider is None:
        provider = GpuProvider(
            slug=snapshot.provider_slug, name=snapshot.provider_name,
            website=snapshot.website, pricing_url=snapshot.pricing_url, kind=snapshot.kind,
        )
        db.add(provider)
        db.flush()
    return provider


def _hash(provider_id: int, q: GpuQuote) -> str:
    import hashlib

    raw = "|".join([
        str(provider_id), q.gpu_model, str(q.price_per_hour), q.currency,
        q.price_kind, str(q.gpu_count), str(q.vram_gb or ""), str(q.region or ""),
    ])
    return hashlib.sha256(raw.encode()).hexdigest()


# Ayni GPU ailesinde on-demand medyanin bu katindan ucuz teklifler "supheli" sayilir.
# Amac: pazaryeri/topluluk ilanlarindaki aykiri (ör. H200 icin 0.50 $) degerlerin
# varsayilan karsilastirmayi bozmasini engellemek.
OUTLIER_FACTOR = 0.35


def _drop_outliers(quotes: list[GpuQuote]) -> tuple[list[GpuQuote], list[GpuQuote]]:
    from statistics import median

    keep: list[GpuQuote] = []
    dropped: list[GpuQuote] = []
    by_family: dict[str, list[Decimal]] = {}
    for q in quotes:
        if q.price_kind == "on_demand":
            by_family.setdefault(family_of(q.gpu_model), []).append(q.price_per_hour)

    for q in quotes:
        family = family_of(q.gpu_model)
        base = by_family.get(family)
        if base and q.price_kind in ("community", "spot"):
            med = median(base)
            if q.price_per_hour < med * Decimal(str(OUTLIER_FACTOR)):
                dropped.append(q)
                continue
        keep.append(q)
    return keep, dropped


def ingest(db: Session, snapshot: GpuSnapshot) -> tuple[int, int]:
    """Donen: (yeni kayit, atlanan). Ayni icerik ikinci kez yazilmaz."""
    provider = get_or_create_provider(db, snapshot)
    quotes, dropped = _drop_outliers(snapshot.quotes)
    if dropped:
        snapshot.quotes = quotes
    created = skipped = 0
    now = dt.datetime.now(dt.timezone.utc)
    batch_keys: set[str] = set()   # ayni partide tekrar eden satirlari ele

    for quote in snapshot.quotes:
        key = _hash(provider.id, quote)
        if key in batch_keys:
            skipped += 1
            continue
        batch_keys.add(key)
        if db.scalar(select(GpuPrice.id).where(GpuPrice.content_hash == key)):
            skipped += 1
            continue
        db.add(GpuPrice(
            provider_id=provider.id,
            gpu_model=quote.gpu_model[:96],
            gpu_family=family_of(quote.gpu_model)[:24],
            vram_gb=quote.vram_gb,
            gpu_count=quote.gpu_count,
            price_per_hour=quote.price_per_hour,
            currency=quote.currency,
            price_kind=quote.price_kind,
            min_lease_hours=quote.min_lease_hours,
            region=quote.region,
            source_url=snapshot.pricing_url,
            observed_at=now,
            status="approved",   # GPU fiyati kaynaktan dogrudan okunur; QA asagida
            content_hash=key,
            raw_payload=str(quote.raw)[:2000] if quote.raw else None,
            notes=quote.notes,
        ))
        created += 1

    db.commit()
    return created, skipped