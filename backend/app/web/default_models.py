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
