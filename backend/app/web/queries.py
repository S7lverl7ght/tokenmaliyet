"""Paylasilan veri erisim katmani.

Arayuz bilesenleri dogrudan SQL yazmaz; buradaki fonksiyonlar uzerinden veri alir.
Boylece API ve web katmani ayni kurallari uygular (yalnizca approved, kanal ayrimi vb.).
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from ..models import DataSource, ExchangeRate, Model, PriceObservation, Provider

# Saglayici bazli model sayfasi URL'leri: kullanici "Kaynak" tiklayinca HAM VERI degil,
# saglayicinin KENDI model kartina gitmeli. Bilinmeyen saglayici icin fiyat sayfasi kullanilir.
PROVIDER_MODEL_URL = {
    "openai": "https://platform.openai.com/docs/models/{slug}",
    "anthropic": "https://docs.anthropic.com/en/docs/about-claude/models/overview",
    "gemini": "https://ai.google.dev/gemini-api/docs/models/{slug}",
    "deepseek": "https://api-docs.deepseek.com/quick_start/pricing",
    "openrouter": "https://openrouter.ai/{slug}",
} 

PROVIDER_FALLBACK_URL = {
    "openai": "https://platform.openai.com/docs/models",
    "anthropic": "https://www.anthropic.com/pricing",
    "gemini": "https://ai.google.dev/gemini-api/docs/models",
    "deepseek": "https://api-docs.deepseek.com/quick_start/pricing",
    "openrouter": "https://openrouter.ai/models",
} 


def model_page_url(provider_slug: str, model_name: str) -> str:
    """Modelin saglayici sitesindeki kendi sayfasi (ham veri degil)."""
    template = PROVIDER_MODEL_URL.get(provider_slug)
    if not template:
        return PROVIDER_FALLBACK_URL.get(provider_slug, "")
    return template.format(slug=model_name)

APPROVED = "approved"
STALE_DAYS = 45

DIMENSIONS: dict[str, str] = {
    "input": "Girdi (input)",
    "output": "Cikti (output)",
    "cache_read": "Onbellek okuma (cache read)",
    "cache_write": "Onbellek yazma (cache write)",
    "image_input": "Gorsel girdi",
    "image_output": "Gorsel cikti",
    "audio_input": "Ses girdi",
    "audio_output": "Ses cikti",
    "request": "Istek",
    "second": "Saniye",
    "gpu_hour": "GPU-saat",
}
TOKEN_DIMS = {"input", "output", "cache_read", "cache_write"}


@dataclass
class PriceRow:
    model_id: int
    slug: str
    provider_slug: str
    provider_name: str
    name: str
    variant: str | None
    channel: str
    source_url: str
    observed_at: dt.datetime
    dims: dict[str, dict] = field(default_factory=dict)
    model_url: str = ""
    is_alias: bool = False
    alias_of: str | None = None

    def dim(self, key: str) -> dict | None:
        return self.dims.get(key)

    @property
    def has_tokens(self) -> bool:
        return "input" in self.dims and "output" in self.dims


def split_variant(canonical_id: str) -> tuple[str, str | None]:
    """google/gemini-4-carbon:batch -> (google/gemini-4-carbon, batch).

    Kilavuz kurali: ana model tek sayfa, varyantlar etiket. Slug varyant eki tasimaz.
    """
    base, _, variant = canonical_id.partition(":")
    return base, (variant or None)


def to_slug(base: str) -> str:
    """Model kimliginden URL-guvenli slug uretir; / ayirici kalir."""
    out: list[str] = []
    for ch in base.strip().lower():
        if ch.isascii() and ch.isalnum():
            out.append(ch)
        elif ch == "/":
            out.append("/")
        elif ch in "-_.":
            out.append(ch if ch != "_" else "-")
    raw = "".join(out)
    parts = [p.strip("-.") for p in raw.split("/")]
    parts = [p for p in parts if p]
    return "/".join(parts) or "model"


def get_fx(session: Session, quote: str = "TRY") -> ExchangeRate | None:
    return session.scalars(
        select(ExchangeRate)
        .where(ExchangeRate.quote_currency == quote)
        .order_by(desc(ExchangeRate.effective_at))
    ).first()


def last_checked(session: Session) -> dt.datetime | None:
    return session.scalar(
        select(func.max(PriceObservation.observed_at)).where(PriceObservation.status == APPROVED)
    )


def providers(session: Session) -> list[Provider]:
    return list(session.scalars(select(Provider).where(Provider.is_active.is_(True)).order_by(Provider.name)))


def _collect(session: Session, *, provider_slug: str | None = None) -> list[PriceRow]:
    stmt = (
        select(PriceObservation, Model, Provider, DataSource)
        .join(Model, Model.id == PriceObservation.model_id)
        .join(Provider, Provider.id == Model.provider_id)
        .join(DataSource, DataSource.id == PriceObservation.source_id)
        .where(PriceObservation.status == APPROVED)
        .order_by(desc(PriceObservation.observed_at))
    )
    if provider_slug:
        stmt = stmt.where(Provider.slug == provider_slug)

    rows: dict[int, PriceRow] = {}
    for obs, model, provider, source in session.execute(stmt).all():
        row = rows.get(model.id)
        base, variant = split_variant(model.canonical_id)
        if row is None:
            row = rows[model.id] = PriceRow(
                model_id=model.id, slug=to_slug(base), provider_slug=provider.slug,
                provider_name=provider.name, name=base, variant=variant,
                channel=source.sales_channel, source_url=source.source_url,
                observed_at=obs.observed_at,
                model_url=model_page_url(provider.slug, base) or provider.pricing_url,
            )
        # Ayni boyut+donem ikilisi bir kez tutulur; peak ve off-peak AYRI anahtar olarak saklanir,
        # boylece detay sayfasinda ikisi de gorunur ve hicbiri digerinin yerine gecmez.
        slot = obs.price_dimension if obs.peak_period != "peak" else f"{obs.price_dimension}:peak"
        if slot in row.dims:
            continue
        row.dims[slot] = {
            "dimension": obs.price_dimension,
            "amount": float(obs.amount),
            "currency": obs.currency,
            "billing_unit": obs.billing_unit,
            "usd_per_1m": float(obs.normalized_usd_per_1m) if obs.normalized_usd_per_1m is not None else None,
            "peak_period": obs.peak_period,
            "tier_label": obs.tier_label,
            "observed_at": obs.observed_at,
            "effective_from": obs.effective_from,
            "source_url": source.source_url,
            "channel": source.sales_channel,
        }
    return list(rows.values())


def _price_signature(row: PriceRow) -> tuple:
    """Fiyat imzasi: ayni imza + ayni saglayici = buyuk olasilikla alias."""
    inp = row.dim("input")
    out = row.dim("output")
    return (
        round(inp["amount"] * 1_000_000, 6) if inp else None,
        round(out["amount"] * 1_000_000, 6) if out else None,
    )


def mark_aliases(rows: list[PriceRow]) -> list[PriceRow]:
    """'~' ile baslayan '...-latest' kayitlari takma addir; ana modele baglanir.

    Inceleme raporu (11.11.2026) madde 4: alias kayit kendi satirini almamali.
    Kural: id '~' ile basliyorsa ve ayni saglayici icinde AYNI fiyat imzasina sahip
    baska bir kayit varsa -> alias kabul edilir, listede gosterilmez.
    """
    real: dict[tuple, PriceRow] = {}
    for r in rows:
        if not r.name.startswith("~"):
            real.setdefault((r.provider_slug,) + _price_signature(r), r)

    for r in rows:
        r.is_alias = False
        r.alias_of = None
        if r.name.startswith("~"):
            target = real.get((r.provider_slug,) + _price_signature(r))
            if target is not None:
                r.is_alias = True
                r.alias_of = target.name
    return rows


def price_rows(session: Session, *, provider_slug: str | None = None) -> list[PriceRow]:
    return mark_aliases(_collect(session, provider_slug=provider_slug))


def variants_for(session: Session, provider_slug: str, slug: str) -> list[PriceRow]:
    return [r for r in price_rows(session, provider_slug=provider_slug) if r.slug == slug]


def model_detail(session: Session, provider_slug: str, slug: str) -> list[PriceRow]:
    """Ayni slug icin birden fazla varyant (batch/free) olabilir; hepsi doner."""
    return variants_for(session, provider_slug, slug)


def history(session: Session, model_id: int) -> list[PriceObservation]:
    return list(session.scalars(
        select(PriceObservation)
        .where(PriceObservation.model_id == model_id, PriceObservation.status == APPROVED)
        .order_by(desc(PriceObservation.observed_at))
    ))