from __future__ import annotations

import datetime as dt
import hashlib
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from .collectors.base import ParsedPrice, RawSnapshot
from .models import (
    CollectionRun, DataSource, Model, PriceObservation, Provider, VerificationLog,
)

TOLERANCE = {
    "max_daily_change": Decimal("5.0"),
    "stale_days": 45,
}

# --- Veri kalitesi esikleri -------------------------------------------------
# Inceleme raporu (11.11.2026) sonrasi eklendi: kaynaktan gelen aykiri oranlar
# dogrudan yayina cikmasin, insan incelemesine dusssun.
# Oran kontrolu YALNIZCA token bazli fiyatlara uygulanir: gorsel/ses/istek
# fiyatlarinda cikti girdiden ucuz olabilir, bu hata degildir.
RATIO_MIN = Decimal("0.3")
RATIO_MAX = Decimal("30")
TOKEN_UNITS = ("USD/1M_tokens", "USD/token", "USD/1K_tokens")
BATCH_PREMIUM_MAX = Decimal("1.0")   # batch fiyati normalden yuksek olamaz


def _hash_key(source_id: int, model_id: int, p: ParsedPrice) -> str:
    raw = "|".join(
        [
            str(source_id), str(model_id), p.price_dimension, str(p.amount), p.currency,
            p.billing_unit, str(p.unit_quantity), p.tier_label or "", p.peak_period or "",
            p.effective_from.isoformat() if p.effective_from else "",
        ]
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def get_or_create_provider(db: Session, slug: str, name: str, website: str | None, pricing_url: str | None) -> Provider:
    provider = db.scalar(select(Provider).where(Provider.slug == slug))
    if provider is None:
        provider = Provider(slug=slug, name=name, website=website, pricing_url=pricing_url)
        db.add(provider)
        db.flush()
    else:
        provider.pricing_url = pricing_url or provider.pricing_url
    return provider


def get_or_create_source(db: Session, provider: Provider, snapshot: RawSnapshot, source_type: str,
                         retrieval_method: str, sales_channel: str) -> DataSource:
    source = db.scalar(
        select(DataSource).where(DataSource.provider_id == provider.id, DataSource.source_url == snapshot.source_url)
    )
    if source is None:
        source = DataSource(
            provider_id=provider.id,
            label=snapshot.source_label,
            source_url=snapshot.source_url,
            source_type=source_type,
            retrieval_method=retrieval_method,
            sales_channel=sales_channel,
            is_official=True,
        )
        db.add(source)
        db.flush()
    return source


def get_or_create_model(db: Session, provider: Provider, canonical_id: str, display_name: str) -> Model:
    model = db.scalar(
        select(Model).where(Model.provider_id == provider.id, Model.canonical_id == canonical_id)
    )
    if model is None:
        model = Model(provider_id=provider.id, canonical_id=canonical_id, display_name=display_name)
        db.add(model)
        db.flush()
    return model


def ingest(db: Session, provider: Provider, snapshot: RawSnapshot, prices: list[ParsedPrice],
           source_type: str, retrieval_method: str, sales_channel: str) -> tuple[CollectionRun, int]:
    """Store the raw snapshot metadata plus immutable pending observations. Idempotent by content hash."""
    source = get_or_create_source(db, provider, snapshot, source_type, retrieval_method, sales_channel)
    run = CollectionRun(
        source_id=source.id,
        started_at=dt.datetime.fromisoformat(snapshot.fetched_at),
        status="running",
        snapshot_path=snapshot.snapshot_path,
        content_hash=snapshot.content_hash,
    )
    db.add(run)
    db.flush()

    created = 0
    now = dt.datetime.now(dt.timezone.utc)
    for price in prices:
        model = get_or_create_model(db, provider, price.model_id, price.model_display_name)
        key = _hash_key(source.id, model.id, price)
        exists = db.scalar(select(PriceObservation.id).where(PriceObservation.content_hash == key))
        if exists:
            continue
        db.add(
            PriceObservation(
                model_id=model.id,
                source_id=source.id,
                collection_run_id=run.id,
                price_dimension=price.price_dimension,
                amount=price.amount,
                currency=price.currency,
                billing_unit=price.billing_unit,
                unit_quantity=price.unit_quantity,
                normalized_usd_per_1m=price.normalized_usd_per_1m(),
                tier_label=price.tier_label,
                peak_period=price.peak_period,
                observed_at=now,
                effective_from=price.effective_from,
                status="pending",
                content_hash=key,
                raw_payload=price.raw_excerpt,
            )
        )
        created += 1

    run.items_seen = len(prices)
    run.finished_at = dt.datetime.now(dt.timezone.utc)
    run.status = "success" if prices else "partial"
    if not prices:
        run.error_summary = "Kaynaktan fiyat satiri ayiklanamadi (sayfa yapisi degismis olabilir)."
    db.commit()
    return run, created


def validate_observation(db: Session, obs: PriceObservation) -> bool:
    """Deterministic QA gate. Returns True when every check passed (candidate for approval)."""
    checks: list[tuple[str, str, dict]] = []

    def add(name: str, ok: bool, details: dict, warn_only: bool = False) -> None:
        checks.append((name, "pass" if ok else ("warn" if warn_only else "fail"), details))

    add("required_fields", all([obs.model_id, obs.source_id, obs.currency, obs.billing_unit,
                                obs.price_dimension, obs.observed_at]), {"observed_at": str(obs.observed_at)})
    add("non_negative", obs.amount >= 0, {"amount": str(obs.amount)})
    if obs.amount == 0:
        blob = str(obs.raw_payload or "").lower() + " " + str(obs.tier_label or "").lower()
        add("zero_requires_free_marker", ("free" in blob or "ucretsiz" in blob),
            {"note": "Sifir fiyat yalnizca kaynakta 'free' ibaresi varsa kabul edilir"})
    add("currency_iso", obs.currency in {"USD", "EUR", "TRY"}, {"currency": obs.currency})
    add("unit_known", obs.billing_unit.split("/")[-1] in {
        "token", "1M_tokens", "image", "second", "request", "GPU-hour", "1K_tokens",
        "1K_requests", "minute",
    }, {"billing_unit": obs.billing_unit})
    age_days = (dt.datetime.now(dt.timezone.utc) - obs.observed_at).days if obs.observed_at else 999
    add("freshness", age_days <= TOLERANCE["stale_days"], {"age_days": age_days}, warn_only=True)

    # --- Cikti/girdi orani: birim donusumu veya kaynak hatasini yakalar -------
    is_token_price = (obs.billing_unit or "") in TOKEN_UNITS
    if is_token_price and obs.price_dimension in ("input", "output") and obs.model_id:
        obs_of = db.scalars(
            select(PriceObservation).where(
                PriceObservation.model_id == obs.model_id,
                PriceObservation.price_dimension.in_(["input", "output"]),
                PriceObservation.status.in_(["pending", "approved"]),
                PriceObservation.id != obs.id,
            )
        ).all()
        pair = {o.price_dimension: o for o in obs_of}
        pair[obs.price_dimension] = obs
        inp, out = pair.get("input"), pair.get("output")
        if inp is not None and out is not None and float(inp.amount) > 0:
            ratio = Decimal(out.amount) / Decimal(inp.amount)
            ok = RATIO_MIN <= ratio <= RATIO_MAX
            add(
                "output_input_ratio",
                ok,
                {"ratio": float(round(ratio, 4)), "min": float(RATIO_MIN), "max": float(RATIO_MAX),
                 "note": "Cikti/girdi orani aykiri; birim veya kaynak hatasi olabilir" if not ok else "normal aralikta"},
            )

    # --- Ayni model+kalem+donem icin TEK fiyat olmali -----------------------
    # Iki gercek hata bu kurali dogurdu:
    #   1) Anthropic baglam dilimi (<=100K / >100K) etiketsiz kaldigi icin ayni kalem
    #      iki fiyatla yayinlaniyordu.
    #   2) Gemini "Image/Audio/Video input price" satirlari jenerik "input" boyutuna
    #      dustugu icin tek modelde 4 farkli "input" fiyati olusuyordu.
    # Cozum: tier ETIKETINDEN BAGIMSIZ olarak, ayni (model, kalem, donem) icin
    # yalnizca TEK fiyat olabilir. Farkli baglam dilimi varsa bu bir VERI MODELI
    # sorunudur ve insan incelemesi gerekir; sessizce yayinlanmaz.
    twins = db.scalars(
        select(PriceObservation).where(
            PriceObservation.model_id == obs.model_id,
            PriceObservation.price_dimension == obs.price_dimension,
            PriceObservation.peak_period.is_(obs.peak_period) if obs.peak_period is None
            else PriceObservation.peak_period == obs.peak_period,
            PriceObservation.id != obs.id,
            PriceObservation.status.in_(["pending", "approved"]),
        )
    ).all()
    conflicting = [x for x in twins if Decimal(x.amount) != Decimal(obs.amount)]
    add(
        "single_price_per_dimension",
        not conflicting,
        {
            "duplicates": len(conflicting),
            "amounts": sorted({float(x.amount) for x in conflicting})[:6],
            "tiers": sorted({str(x.tier_label) for x in conflicting})[:4],
            "note": ("Ayni kalem icin birden fazla farkli fiyat (baglam dilimi veya "
                     "multimodal etiket ayrimi eksik)") if conflicting else "tek fiyat",
        },
    )

    # --- Batch varyanti normalden pahali olamaz ------------------------------
    if obs.tier_label and "batch" in str(obs.tier_label).lower() and obs.price_dimension in ("input", "output"):
        base = db.scalars(
            select(PriceObservation)
            .where(
                PriceObservation.model_id == obs.model_id,
                PriceObservation.price_dimension == obs.price_dimension,
                PriceObservation.status == "approved",
                PriceObservation.tier_label.is_(None),
            )
            .order_by(PriceObservation.observed_at.desc())
        ).first()
        if base is not None and float(base.amount) > 0:
            mult = Decimal(obs.amount) / Decimal(base.amount)
            add(
                "batch_not_premium",
                mult <= BATCH_PREMIUM_MAX,
                {"multiple_of_base": float(round(mult, 3)),
                 "note": "Batch fiyati normal fiyattan yuksek" if mult > BATCH_PREMIUM_MAX else "batch indirimli"},
            )

    for name, result, details in checks:
        db.add(VerificationLog(observation_id=obs.id, check_name=name, result=result, details=details))
    return all(result != "fail" for _, result, _ in checks)


def approve(db: Session, obs: PriceObservation, actor: str, require_clean_qa: bool = True) -> bool:
    if require_clean_qa:
        fails = db.scalars(
            select(VerificationLog).where(
                VerificationLog.observation_id == obs.id, VerificationLog.result == "fail"
            )
        ).all()
        if fails:
            return False
    obs.status = "approved"
    obs.approved_at = dt.datetime.now(dt.timezone.utc)
    obs.approved_by = actor
    db.add(obs)
    return True


def reject(db: Session, obs: PriceObservation, actor: str, reason: str) -> None:
    obs.status = "rejected"
    obs.approved_by = actor
    db.add(VerificationLog(observation_id=obs.id, check_name="manual_review", result="fail",
                           details={"reason": reason, "actor": actor}))