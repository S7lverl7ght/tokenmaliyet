"""Rehber icerigi.

Kural: her yazi kendi verimizden veya dogrulanabilir kaynaktan gelir; anahtar kelime
doldurmak icin ince sayfa uretilmez. Sayilar elle yazilmaz, veritabanindan gelir.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Guide:
    slug: str
    title: str
    description: str
    updated: str
    published: str
    reading_min: int


GUIDES: list[Guide] = [
    Guide(
        slug="token-maliyeti-nasil-hesaplanir",
        title="Token maliyeti nasıl hesaplanır?",
        description=("Girdi ve çıktı token fiyatlarından aylık maliyet hesaplama, cache ve batch "
                     "indirimlerinin etkisi, sık yapılan hesap hataları."),
        published="04.11.2026",
        updated="11.11.2026",
        reading_min=6,
    ),
    Guide(
        slug="dogrudan-api-ve-pazaryeri-farki",
        title="Doğrudan API ile pazaryeri fiyatı neden aynı değil?",
        description=("OpenRouter gibi pazaryerleri ile sağlayıcının kendi API fiyatı arasındaki fark, "
                     "hangi durumda hangisinin doğru karşılaştırma olduğu."),
        published="06.11.2026",
        updated="11.11.2026",
        reading_min=5,
    ),
    Guide(
        slug="peak-off-peak-fiyatlandirma",
        title="Yoğun saat (peak) fiyatlandırması bütçeyi nasıl değiştirir?",
        description=("DeepSeek gibi sağlayıcılarda yoğun/yoğun olmayan saat fiyat farkı ve bunun "
                     "aylık maliyete etkisi."),
        published="09.11.2026",
        updated="11.11.2026",
        reading_min=4,
    ),
]


def by_slug(slug: str) -> Guide | None:
    for g in GUIDES:
        if g.slug == slug:
            return g
    return None
