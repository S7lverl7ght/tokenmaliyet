"""TEK hesaplama modulu.

Inceleme raporu 3. tur, bulgu 1 ve 2: Karsilastir sayfasi deepseek-v4-pro icin
115,50 USD, Hesaplayici 264,50 USD gosteriyordu (ayni model, ayni token sayisi).
Sebep: hesap mantigi sayfalara dagilmisti.

Kural: Compare, Calculator, Token sayaci ve Tum sayfalar bu modulu kullanir.
Formul tek yerde yasar; degistirmek icin burayi degistirin.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

# Turkce carpani: OLCULMUS deger (backend/app/web/data/turkce_token.json).
# Uygulama kurali (rapor 3. tur): carpan HER IKI modele de uygulanir veya hicbirine.
# Tek tarafli uygulama matematiksel olarak tutarsizdir.


@dataclass
class ModelPrice:
    """Tek bir modelin hesaplamada kullanilan fiyat kaydi."""

    name: str
    provider: str
    slug: str
    input_per_1m: float | None
    output_per_1m: float | None
    cache_read_per_1m: float | None = None
    tier_label: str | None = None       # hangi baglam dilimi kullanildi
    peak_period: str | None = None
    observed_at: object | None = None

    @property
    def usable(self) -> bool:
        return self.input_per_1m is not None and self.output_per_1m is not None


@dataclass
class CostBreakdown:
    model: ModelPrice
    input_usd: float
    output_usd: float
    cache_usd: float
    total_usd: float
    effective_input_tokens: float
    effective_output_tokens: float
    tokens_multiplier: float
    cache_share: float

    @property
    def display(self) -> dict:
        return {
            "name": self.model.name,
            "provider": self.model.provider,
            "slug": self.model.slug,
            "input_usd": self.input_usd,
            "output_usd": self.output_usd,
            "cache_usd": self.cache_usd,
            "total_usd": self.total_usd,
            "tier_label": self.model.tier_label,
            "peak_period": self.model.peak_period,
            "input_per_1m": self.model.input_per_1m,
            "output_per_1m": self.model.output_per_1m,
            "tokens_multiplier": self.tokens_multiplier,
            "cache_share": self.cache_share,
        }


def monthly_cost(
    model: ModelPrice,
    input_tokens: float,
    output_tokens: float,
    *,
    tokens_multiplier: float = 1.0,
    cache_share: float = 0.0,
) -> CostBreakdown:
    """Aylik maliyet. TEK formul - tum sayfalar buradan gecer.

    tokens_multiplier: Turkce icerik varsayimi (her iki modele de ayni uygulanir).
    cache_share: girdinin onbellekten okunan orani (0-0.95).
    """
    mult = max(0.01, min(10.0, float(tokens_multiplier or 1.0)))
    cshare = max(0.0, min(0.95, float(cache_share or 0.0)))

    eff_in = float(input_tokens) * mult
    eff_out = float(output_tokens) * mult

    inp = float(model.input_per_1m or 0.0)
    outp = float(model.output_per_1m or 0.0)
    cache = float(model.cache_read_per_1m or 0.0)

    if cshare > 0 and cache > 0:
        per_m_input = inp * (1 - cshare) + cache * cshare
        cache_usd = (eff_in / 1_000_000) * (cache * cshare)
        input_usd = (eff_in / 1_000_000) * (inp * (1 - cshare))
    else:
        per_m_input = inp
        cache_usd = 0.0
        input_usd = (eff_in / 1_000_000) * inp

    output_usd = (eff_out / 1_000_000) * outp
    total = input_usd + output_usd + (cache_usd if cache_usd else 0.0)

    return CostBreakdown(
        model=model,
        input_usd=input_usd,
        output_usd=output_usd,
        cache_usd=cache_usd,
        total_usd=total,
        effective_input_tokens=eff_in,
        effective_output_tokens=eff_out,
        tokens_multiplier=mult,
        cache_share=cshare,
    )


def compare_models(
    a: ModelPrice,
    b: ModelPrice,
    input_tokens: float,
    output_tokens: float,
    *,
    tokens_multiplier: float = 1.0,
    cache_share: float = 0.0,
) -> dict:
    """Iki modeli AYNI varsayimlarla karsilastirir. Tek kaynak."""
    ca = monthly_cost(a, input_tokens, output_tokens,
                      tokens_multiplier=tokens_multiplier, cache_share=cache_share)
    cb = monthly_cost(b, input_tokens, output_tokens,
                      tokens_multiplier=tokens_multiplier, cache_share=cache_share)
    diff = ca.total_usd - cb.total_usd
    pct = (diff / ca.total_usd * 100) if ca.total_usd else None
    return {
        "a": ca,
        "b": cb,
        "diff_usd": diff,
        "saving_pct": pct,
        "cheaper": "b" if diff > 0 else ("a" if diff < 0 else None),
        "tokens_multiplier": tokens_multiplier,
        "cache_share": cache_share,
    }
