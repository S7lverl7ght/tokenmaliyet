"""Basit iki dilli sozluk.

Kural: kullaniciya gorunen tum metinler burada tanimli olmak zorunda degil;
yaygin gezinme/baslik/etiketler cevrilir, uzun icerik (rehber) Turkce kalir.
Sayfa dili <html lang> olarak da yansitilir (SEO).
"""
from __future__ import annotations

DEFAULT_LANG = "tr"
SUPPORTED = ("tr", "en")

STRINGS: dict[str, dict[str, str]] = {
    # gezinme
    "nav.prices": {"tr": "Fiyatlar", "en": "Prices"},
    "nav.compare": {"tr": "Karşılaştır", "en": "Compare"},
    "nav.calculator": {"tr": "Hesaplayıcı", "en": "Calculator"},
    "nav.token": {"tr": "Token sayacı", "en": "Token counter"},
    "nav.gpu": {"tr": "GPU maliyetleri", "en": "GPU costs"},
    "nav.guides": {"tr": "Rehber", "en": "Guides"},
    "nav.about": {"tr": "Hakkında", "en": "About"},
    "nav.search": {"tr": "Model ara", "en": "Find a model"},
    "theme.toggle": {"tr": "Koyu temaya geç", "en": "Switch to dark theme"},
    "theme.toggle.light": {"tr": "Açık temaya geç", "en": "Switch to light theme"},
    "a11y.skip": {"tr": "İçeriğe geç", "en": "Skip to content"},

    # tablo
    "col.model": {"tr": "Model", "en": "Model"},
    "col.provider": {"tr": "Sağlayıcı", "en": "Provider"},
    "col.channel": {"tr": "Kanal", "en": "Channel"},
    "col.input": {"tr": "Girdi fiyatı", "en": "Input price"},
    "col.output": {"tr": "Çıktı fiyatı", "en": "Output price"},
    "col.updated": {"tr": "Güncelleme", "en": "Updated"},
    "col.source": {"tr": "Model sayfası", "en": "Model page"},

    # ortak
    "common.source": {"tr": "Kaynak", "en": "Source"},
    "common.clear": {"tr": "Filtreleri temizle", "en": "Clear filters"},
    "common.apply": {"tr": "Uygula", "en": "Apply"},
    "common.currency": {"tr": "Para birimi", "en": "Currency"},
    "common.language": {"tr": "Dil", "en": "Language"},
}


def t(key: str, lang: str = DEFAULT_LANG) -> str:
    entry = STRINGS.get(key, {})
    return entry.get(lang) or entry.get(DEFAULT_LANG) or key
