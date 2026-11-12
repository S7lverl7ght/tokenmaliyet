"""Varsayilan model secimleri - TEK kaynak.

Inceleme raporu (11.11.2026) madde 7: Hesaplayici claude-sonnet-4.5, Karsilastir ve
Token sayaci claude-fable-5 seciliyordu. Artik hepsi buradan okur.
"""
from __future__ import annotations

# Tercih sirasi: ilk bulunan kullanilir. Model adlari saglayici sayfalarindan dogrulanmistir.
PREFERRED_PRIMARY = ("claude-sonnet-4.5", "claude-sonnet-5", "gpt-6-1-sol", "gemini-2.5-pro")
PREFERRED_ALTERNATIVE = ("deepseek-v4-pro", "deepseek-flash", "gpt-6-luna", "gemini-2.5-flash")

# Token sayaci icin tek varsayilan
PREFERRED_COUNTER = ("claude-sonnet-4.5", "gpt-6-1-sol", "gemini-2.5-pro", "deepseek-v4-pro")


def pick(rows, needles: tuple[str, ...], *, channel: str | None = "direct", require_tokens: bool = True):
    """Ada gore ilk uygun modeli secer; bulamazsa ucuz dogrudan modeli dondurur."""
    pool = [r for r in rows if (not require_tokens or r.has_tokens)]
    if channel:
        pool = [r for r in pool if r.channel == channel]
    for needle in needles:
        for r in pool:
            if r.name == needle:
                return r
    if not pool:
        return None
    from .render import price_value

    return sorted(pool, key=lambda r: (price_value(r.dim("input"))[0] or 0))[0]


def key(row) -> str:
    return f"{row.provider_slug}|{row.slug}|{row.variant or ''}"


# Inceleme raporu (12.11.2026): "498 model sayfasi 'thin content' riski.
# Ilk fazda yalnizca en cok aranan 30-50 model indekslensin."
# Bu liste dogrudan saglayicilarin bilinen modelleridir; digerleri noindex + sitemap disi.
INDEXABLE_PROVIDERS = ("openai", "anthropic", "gemini", "deepseek")

INDEXABLE_FAMILIES = (
    "gpt-6", "gpt-5", "o3", "o4",
    "claude-opus", "claude-sonnet", "claude-haiku", "claude-fable",
    "gemini-2.5", "gemini-3", "gemini-4",
    "deepseek-flash", "deepseek-v4",
)


def is_indexable(row) -> bool:
    """Model sayfasi indekslenmeli mi?

    Kural: dogrudan saglayici + bilinen aile + alias degil + token fiyati var.
    Boylece 400+ ince sayfa yerine ~40 derin sayfa indekslenir.
    """
    if row.channel != "direct" or row.is_alias:
        return False
    if row.provider_slug not in INDEXABLE_PROVIDERS:
        return False
    if not row.has_tokens:
        return False
    name = row.name.lower()
    return any(name.startswith(fam) or fam in name for fam in INDEXABLE_FAMILIES)
