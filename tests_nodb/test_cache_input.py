"""Onbellek okuma orani: serbest giris testleri.

Kullanici istegi (12.11.2026): sabit %25/%50/%75 secenekleri yerine kullanici
kendi oranini girebilmeli. Metin dili alani da digerleriyle uyumlu genislikte olmali.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CALC = ROOT / "backend" / "app" / "web" / "templates" / "calculator.html"
ROUTES = ROOT / "backend" / "app" / "web" / "routes.py"
CSS = ROOT / "backend" / "app" / "web" / "static" / "app.css"


def test_cache_is_text_input_not_select():
    html = CALC.read_text(encoding="utf-8")
    m = re.search(r'<input id="cache"([^>]*)>', html)
    assert m, "cache alani input olmali (select degil)"
    assert 'type="text"' in m.group(1)
    assert 'inputmode="numeric"' in m.group(1)
    # sabit secenekler kalmamali
    assert '<select id="cache"' not in html, "sabit yuzde secenekleri kaldirilmali"


def test_cache_validated_in_route():
    src = ROUTES.read_text(encoding="utf-8")
    assert 'errors["cache"]' in src, "gecersiz onbellek degeri kullaniciya bildirilmeli"
    assert "0 ile 95" in src or "0–95" in src, "aralik aciklanmali"
    # yuzde isareti ve virgul kabul edilmeli
    assert 'replace("%", "")' in src
    assert 'replace(",", ".")' in src


def test_cache_affects_cost():
    """Onbellek orani maliyeti gercekten degistirmeli (formul bagli)."""
    src = ROOT / "backend" / "app" / "web" / "calc.py"
    body = src.read_text(encoding="utf-8")
    assert "cache_share" in body
    assert "cache_read_per_1m" in body
    # onbellek fiyati varsa girdi maliyeti karisim olmali
    assert "per_m_input" in body or "(1 - cshare)" in body


def test_language_field_same_width_as_others():
    html = CALC.read_text(encoding="utf-8")
    # uc esit kolonlu grid
    assert "1fr 1fr 1fr" in html, "alanlar esit genislikte olmali"
    css = CSS.read_text(encoding="utf-8")
    assert ".calc-tight #dil" in css, "dil alani genislik kurali yok"
    assert "max-width:110px" in css, "onbellek alani dar olmali"
