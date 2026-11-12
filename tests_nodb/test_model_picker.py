"""Model secici: tum modeller + isimden arama testleri.

Kullanici istegi (12.11.2026): hesaplayicida tum modeller listelenmiyordu
(yalnizca 49 dogrudan model) ve isimden arama yoktu. 487 modelin tamami
listelenmeli ve yazarak filtrelenebilmeli.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CALC = ROOT / "backend" / "app" / "web" / "templates" / "calculator.html"
ROUTES = ROOT / "backend" / "app" / "web" / "routes.py"
BASE = ROOT / "backend" / "app" / "web" / "templates" / "base.html"


def test_calculator_uses_all_models():
    """direct_only=False olmali; aksi halde yalnizca ~49 model listelenir."""
    src = ROUTES.read_text(encoding="utf-8")
    i = src.index("def calculator_page")
    j = src.index("def ", i + 10)
    body = src[i:j]
    assert "_model_options(rows, direct_only=False)" in body, (
        "hesaplayici tum modelleri kullanmali"
    )
    assert "direct_only=True" not in body


def test_options_embedded_as_json():
    html = CALC.read_text(encoding="utf-8")
    assert "__MODEL_OPTIONS__" in html, "model listesi JS'e gomulmemis"
    assert "options|tojson" in html, "JSON serilestirme yok"


def test_picker_replaces_select():
    html = CALC.read_text(encoding="utf-8")
    assert 'data-picker' in html, "aranabilir secici yok"
    assert 'class="picker-input"' in html, "arama girdisi yok"
    assert 'role="combobox"' in html, "erisilebilir combobox rolu yok"
    assert 'role="listbox"' in html, "erisilebilir listbox yok"
    # eski select kalmamali
    assert 'data-model-options' not in html
    assert '<select id="from"' not in html


def test_hidden_input_carries_value():
    """JS kapali olsa bile form gonderilebilmeli: gizli input degeri tasir."""
    html = CALC.read_text(encoding="utf-8")
    assert '<input type="hidden" id="from" name="from"' in html
    assert '<input type="hidden" id="to" name="to"' in html


def test_search_normalizes_turkish_and_case():
    html = CALC.read_text(encoding="utf-8")
    assert "toLocaleLowerCase" in html, "kucuk harfe cevirme yok"
    for ch in ["ı", "ş", "ğ", "ü", "ö", "ç"]:
        assert f'/{ch}/g' in html or f'"{ch}"' in html, f"{ch} normalizasyonu yok"


def test_search_tolerates_spaces():
    html = CALC.read_text(encoding="utf-8")
    # bosluk/tire normalizasyonu + kelime bazli eslesme
    assert "\\s\\-_./" in html or "[\\s\\-_./]" in html, "bosluk normalizasyonu yok"
    assert "parts.every" in html, "kelime bazli arama yok"


def test_keyboard_navigation_supported():
    html = CALC.read_text(encoding="utf-8")
    assert "ArrowDown" in html and "ArrowUp" in html, "klavye gezinmesi yok"
    assert 'e.key === "Enter"' in html, "Enter ile secim yok"
    assert "Escape" in html, "Escape ile kapatma yok"


def test_obsolete_select_filler_removed():
    """base.html'deki eski select doldurucu kaldirilmali (artik select yok)."""
    base = BASE.read_text(encoding="utf-8")
    assert "select[data-model-options]" not in base
