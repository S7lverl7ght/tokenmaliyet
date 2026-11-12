"""Cok dilli ve para birimi testleri.

Gercek hatalar (12.11.2026):
  1. CSP, Cloudflare Web Analytics beacon'ini engelliyordu (script-src).
  2. /fiyatlar?lang=en Ingilizce'ye gecmiyordu: statik sitede query string
     sunucuda islenmiyor. Cozum: /en/ ve /try/ yollari gercek sayfa olarak uretildi.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.web.i18n import STRINGS, SUPPORTED, t as translate  # noqa: E402


def test_every_key_has_both_languages():
    missing = [k for k, v in STRINGS.items() if not v.get("tr") or not v.get("en")]
    assert not missing, f"eksik ceviri: {missing[:8]}"


def test_t_falls_back_to_turkish():
    assert translate("nav.prices", "tr") == "Fiyatlar"
    assert translate("nav.prices", "en") == "Prices"
    # bilinmeyen dil -> TR
    assert translate("nav.prices", "de") == "Fiyatlar"


def test_unknown_key_returns_key():
    assert translate("yok.boyle.anahtar", "en") == "yok.boyle.anahtar"


def test_key_count_is_substantial():
    # Sayfa metinlerinin cogu cevrilmis olmali.
    assert len(STRINGS) >= 180, f"sozluk kucuk: {len(STRINGS)}"


def test_no_turkish_only_values_in_english():
    """EN degerinde Turkce'ye ozgu karakter olmamali (ceviri gercekten yapilmis)."""
    bad = []
    for k, v in STRINGS.items():
        en = v.get("en", "")
        if any(ch in en for ch in "çğıöşüÇĞİÖŞÜ"):
            bad.append(k)
    assert not bad, f"Ingilizce degerde Turkce karakter: {bad[:6]}"


def test_csp_allows_cloudflare_analytics():
    src = (ROOT / "scripts" / "export_static.py").read_text(encoding="utf-8")
    assert "static.cloudflareinsights.com" in src, "CSP beacon'a izin vermiyor"
    assert "connect-src 'self' https://cloudflareinsights.com" in src


def test_hreflang_pairs_defined():
    src = (ROOT / "backend" / "app" / "web" / "render.py").read_text(encoding="utf-8")
    assert "_hreflang_pairs" in src
    assert "x-default" in src, "x-default hreflang eksik"


def test_lang_and_currency_are_independent():
    """Dil ve para birimi BAGIMSIZ secilmeli.

    Gercek hata (12.11.2026): TRY secince dil TR'ye, USD secince dil EN'ye
    zorla donuyordu; kullanici istedigi kombinasyonu secemiyordu.
    """
    from app.web.render import _build_path, _parse_path

    # Okuma
    assert _parse_path("/fiyatlar") == ("tr", "USD", "/fiyatlar")
    assert _parse_path("/en/fiyatlar") == ("en", "USD", "/fiyatlar")
    assert _parse_path("/try/fiyatlar") == ("tr", "TRY", "/fiyatlar")
    assert _parse_path("/en/try/fiyatlar") == ("en", "TRY", "/fiyatlar")

    # Yazma: dort kombinasyon da ayri yol uretmeli
    assert _build_path("tr", "USD", "/fiyatlar") == "/fiyatlar"
    assert _build_path("en", "USD", "/fiyatlar") == "/en/fiyatlar"
    assert _build_path("tr", "TRY", "/fiyatlar") == "/try/fiyatlar"
    assert _build_path("en", "TRY", "/fiyatlar") == "/en/try/fiyatlar"


def test_switching_language_keeps_currency():
    from app.web.render import _build_path, _parse_path

    # TR/TRY sayfasinda dil degistir -> TRY korunmali
    lang, cur, base = _parse_path("/try/fiyatlar")
    assert _build_path("en", cur, base) == "/en/try/fiyatlar"
    # EN/TRY sayfasinda dil degistir -> TRY korunmali
    lang, cur, base = _parse_path("/en/try/fiyatlar")
    assert _build_path("tr", cur, base) == "/try/fiyatlar"


def test_switching_currency_keeps_language():
    from app.web.render import _build_path, _parse_path

    lang, cur, base = _parse_path("/en/fiyatlar")
    assert _build_path(lang, "TRY", base) == "/en/try/fiyatlar"
    lang, cur, base = _parse_path("/en/try/fiyatlar")
    assert _build_path(lang, "USD", base) == "/en/fiyatlar"


def test_export_creates_all_four_combinations():
    src = (ROOT / "scripts" / "export_static.py").read_text(encoding="utf-8")
    assert "VARIANTS" in src
    assert '"/fiyatlar", "fiyatlar", "en", "TRY"' in src, "EN/TRY varyanti yok"
    assert '"en", "USD"' in src and '"tr", "TRY"' in src
    assert '"/gpu-maliyetleri", "gpu-maliyetleri", "en", "TRY"' in src, "EN/TRY GPU varyanti yok"
