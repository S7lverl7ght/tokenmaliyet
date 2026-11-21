# -*- coding: utf-8 -*-
"""12. tur: hesaplayici ve medya hesaplayici arayuz hatalari (21.11.2026).

Bulunanlar:
  1. Grafik cubuklari recalc() icinde guncellenmiyordu (sabit kaliyordu).
  2. Kart ve grafik farkli yuvarlama kullaniyordu (211,83 vs 211,82).
  3. Hizli token cipleri "input" olayi tetiklemiyordu -> sonuc guncellenmiyordu.
  4. Onbellek hesaba katilirken metin "onbellek hesaba katilmadi" diyordu.
  5. input[type="email"] app.css'te yoktu -> bulten alani kisa kaliyordu.
  6. .notice-ok sinifi CSS'te yoktu -> basari mesaji renksizdi.
  7. Ses/medya: tur degisince tablo degismiyor, submit sayfayi sifirliyordu.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

DIST = ROOT / "dist"
TPLS = ROOT / "backend" / "app" / "web" / "templates"
CSS = ROOT / "backend" / "app" / "web" / "static" / "app.css"
CALC = TPLS / "calculator.html"
MEDIA = TPLS / "ses_maliyeti.html"


# ------------------------------------------------------------------ CSS
def test_email_input_has_styles():
    """input[type=email] de diger metin alanlariyla ayni stili almali."""
    css = CSS.read_text(encoding="utf-8")
    m = re.search(r'input\[type="text"\][^{]*\{', css)
    assert m, "temel input secici yok"
    assert 'input[type="email"]' in m.group(0), "email seciciye eklenmemis"


def test_notice_ok_class_exists():
    css = CSS.read_text(encoding="utf-8")
    assert re.search(r"\.notice-ok\s*\{", css), ".notice-ok CSS'te yok"
    assert re.search(r"\[hidden\]\s*\{\s*display:\s*none", css), "[hidden] kurali yok"


# ------------------------------------------------------------------ Hesap JS
def test_chart_nodes_have_data_roles():
    src = CALC.read_text(encoding="utf-8")
    for role in ("chart-from-usd", "chart-to-usd", "chart-from-bar", "chart-to-bar"):
        assert f'data-role="{role}"' in src, f"{role} yok"


def test_recalc_updates_chart():
    src = CALC.read_text(encoding="utf-8")
    i = src.index("function recalc()")
    body = src[i:i + 4200]
    for role in ("chart-from-usd", "chart-to-usd", "chart-from-bar", "chart-to-bar"):
        assert role in body, f"recalc grafigi guncellemiyor: {role}"


def test_single_rounding_helper():
    src = CALC.read_text(encoding="utf-8")
    assert "function usdFixed" in src, "tek yuvarlama yardimcisi yok"
    # kart ve grafik ayni yardimciyi kullanmali
    i = src.index("function recalc()")
    body = src[i:i + 4200]
    assert body.count("usdFixed(") >= 4, "kart/grafik ayni yardimciyi kullanmiyor"


def test_chip_click_dispatches_input():
    src = CALC.read_text(encoding="utf-8")
    # JS blogundaki cip isleyicisini bul (HTML'deki data-chips degil).
    i = src.index('querySelectorAll("[data-chips]")')
    body = src[i:i + 900]
    assert 'dispatchEvent(new Event("input"' in body, "cip input olayi tetiklemiyor"


def test_cache_note_is_dynamic():
    src = CALC.read_text(encoding="utf-8")
    assert 'data-role="cache-note"' in src
    assert "data-cache-on" in src and "data-cache-off" in src, "onbellek metni dinamik degil"
    # celisen sabit ifade kalmamali
    assert "Önbellek (cache) ve toplu (batch) indirimleri hesaba katılmamıştır." not in src


# ------------------------------------------------------------------ Medya JS
def test_media_passes_all_groups():
    src = MEDIA.read_text(encoding="utf-8")
    assert "window.__MEDIA_ROWS__" in src
    assert "all_rows|tojson" in src
    routes = (ROOT / "backend" / "app" / "web" / "routes.py").read_text(encoding="utf-8")
    assert "all_rows=all_rows" in routes


def test_media_rerenders_table_on_group_change():
    src = MEDIA.read_text(encoding="utf-8")
    assert "function renderTable" in src
    i = src.index('grup.addEventListener("change"')
    assert "renderTable" in src[i:i + 400], "tur degisiminde tablo yeniden cizilmiyor"


def test_media_submit_always_prevented():
    """Form submit HER ZAMAN engellenmeli; aksi halde sayfa sifirlanir."""
    src = MEDIA.read_text(encoding="utf-8")
    i = src.index('form.addEventListener("submit"')
    body = src[i:i + 400]
    assert "e.preventDefault()" in body
    # kosullu engelleme kalmamali
    assert "__STATIC__" not in body, "submit hala kosullu engelleniyor"


# ------------------------------------------------------------------ Uretilen cikti
@pytest.mark.skipif(not DIST.exists(), reason="dist/ yok")
def test_built_calculator_has_chart_hooks():
    html = (DIST / "hesaplayici" / "index.html").read_text(encoding="utf-8", errors="ignore")
    assert "chart-from-bar" in html and "usdFixed" in html


@pytest.mark.skipif(not DIST.exists(), reason="dist/ yok")
def test_built_media_has_group_data():
    html = (DIST / "hesaplayici" / "ses-maliyeti" / "index.html").read_text(encoding="utf-8", errors="ignore")
    m = re.search(r"window\.__MEDIA_ROWS__ = (\{.*?\});", html, re.S)
    assert m, "gomulu grup verisi yok"
    data = json.loads(m.group(1))
    assert set(data.keys()) == {"tts", "stt", "image", "video"}, data.keys()
    for g, rows in data.items():
        assert rows, f"{g} bos"
        assert all("divisor" in r and "usd_per_unit" in r for r in rows), f"{g} alan eksik"
