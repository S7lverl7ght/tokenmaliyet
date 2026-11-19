"""Karsilastirma ciftleri — TEK kaynak.

Neden ayri modul: hem sitemap (routes.py) hem statik export (scripts/export_static.py)
ayni cift listesini kullanmali. Iki yerde ayri mantik olunca sitemap ile gercek
sayfalar kayiyordu (sitemap'te olmayan sayfa / 404 veren kayit).

Kural: once GERCEK arama talebi olan elle secilmis ciftler, sonra kalan
indekslenebilir modellerin kombinasyonlari. Veritabaninda olmayan model atlanir.
"""
from __future__ import annotations

# Elle secilmis, aranan ciftler ("claude vs gpt", "deepseek vs gpt" gibi).
PREFERRED_PAIRS: list[tuple[str, str]] = [
    ("claude-sonnet-4.5", "gpt-6-astra"),
    ("claude-sonnet-4.5", "deepseek-v4-pro"),
    ("claude-sonnet-4.5", "gemini-2.5-pro"),
    ("claude-sonnet-4.5", "gpt-6-luna"),
    ("claude-opus-5", "gpt-6-astra"),
    ("claude-opus-5", "deepseek-v4-pro"),
    ("claude-opus-5", "gemini-2.5-pro"),
    ("gpt-6-astra", "gemini-2.5-pro"),
    ("gpt-6-astra", "deepseek-v4-pro"),
    ("gpt-6-luna", "deepseek-flash"),
    ("gpt-6-luna", "gemini-2.5-flash"),
    ("gemini-2.5-pro", "deepseek-v4-pro"),
    ("claude-haiku-4.5", "gemini-2.5-flash"),
    ("claude-haiku-4.5", "deepseek-flash"),
    ("gemini-2.5-flash", "deepseek-flash"),
    ("claude-sonnet-5", "claude-opus-5"),
    ("claude-sonnet-4.6", "claude-opus-4.8"),
    ("gpt-6-1-sol", "gpt-6-luna"),
    ("gemini-3-flash-preview", "gemini-2.5-flash"),
    ("claude-fable-5", "claude-opus-5"),
]

MAX_PAIRS = 60


def _kind(name: str) -> str:
    """Modelin isi: chat | image | audio | embedding.

    Neden: "flash-lite vs pro-image" gibi ciftler anlamsiz. Yalnizca ayni isi
    goren modeller karsilastirilir; aksi halde arama talebi olmayan ince sayfa olur.
    """
    low = (name or "").lower()
    if any(h in low for h in ("embedding", "-image", "dall-e", "imagen", "flux", "tts",
                              "transcribe", "whisper", "audio", "live", "rerank",
                              "moderation", "robotics", "omni")):
        if any(h in low for h in ("-image", "dall-e", "imagen", "flux")):
            return "image"
        if any(h in low for h in ("tts", "transcribe", "whisper", "audio", "live")):
            return "audio"
        return "other"
    return "chat"


def _similar_kind(a, b) -> bool:
    """Iki model ayni isi goruyor mu?"""
    return _kind(a.name) == _kind(b.name) == "chat"


def comparison_pairs(rows, is_indexable=None) -> list[tuple]:
    """(a, b) ciftleri dondurur; yalnizca ANLAMLI (ayni isi goren) ciftler."""
    import itertools

    if is_indexable is not None:
        pool = [r for r in rows if is_indexable(r)]
    else:
        from . import default_models as dm

        pool = [r for r in rows if dm.is_indexable(r)]

    by_name = {}
    for r in pool:
        by_name.setdefault(r.name, r)

    out: list[tuple] = []
    seen: set[tuple[str, str]] = set()

    # 1) Elle secilmis ARANAN ciftler (aynı işi gören modeller)
    for na, nb in PREFERRED_PAIRS:
        a, b = by_name.get(na), by_name.get(nb)
        if a is None or b is None:
            continue
        if not _similar_kind(a, b):
            continue
        key = tuple(sorted((a.name, b.name)))
        if key in seen:
            continue
        seen.add(key)
        out.append((a, b))

    # 2) Sohbet modelleri arasinda capraz-saglayici kombinasyonlar
    chats = [r for r in pool if _kind(r.name) == "chat"]
    for a, b in itertools.combinations(chats[:12], 2):
        if a.provider_slug == b.provider_slug:
            continue  # ayni saglayici icinde ust/alt segment zaten elle secildi
        key = tuple(sorted((a.name, b.name)))
        if key in seen:
            continue
        seen.add(key)
        out.append((a, b))
        if len(out) >= MAX_PAIRS:
            break

    return out[:MAX_PAIRS]
