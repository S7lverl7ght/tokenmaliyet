"""Ses/gorsel/video maliyet hesaplayici testleri (8. tur).

Arastirma sonucu (ARASTIRMA_VRAM_MEDYA.md): ses ayağı en yuksek ROI,
ElevenLabs affiliate %22, TR arama talebi gercek. Bu testler sozlesmeyi kilitler.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "media_prices.json"


def test_media_prices_file_exists():
    assert DATA.exists(), "media_prices.json yok"
    d = json.loads(DATA.read_text(encoding="utf-8"))
    for group in ("tts", "stt", "image", "video"):
        assert d.get(group), f"{group} grubu bos"


def test_every_price_has_source():
    """Uydurma fiyat olmamali: her kayit kaynak URL tasimali."""
    d = json.loads(DATA.read_text(encoding="utf-8"))
    for group in ("tts", "stt", "image", "video"):
        for row in d[group]:
            assert row.get("source", "").startswith("http"), f"kaynaksiz fiyat: {row}"
            assert float(row["usd_per_unit"]) > 0, f"sifir fiyat: {row}"


def test_cost_calculation_matches_formula():
    """maliyet = miktar x birim fiyat."""
    import sys
    sys.path.insert(0, str(ROOT / "backend"))
    from app.web import media_cost as M

    # 10.000 karakter ElevenLabs v4 = 10K x 0.08 = 0.80 USD
    r = M.cost("tts", "ElevenLabs|v4", 10000)
    assert r is not None
    assert abs(r["usd"] - 0.80) < 1e-6, r

    # 60 dakika Whisper = 60 x 0.006 = 0.36 USD
    r2 = M.cost("stt", "OpenAI|Whisper", 60)
    assert abs(r2["usd"] - 0.36) < 1e-6, r2

    # 100 gorsel FLUX = 100 x 0.041 = 4.10 USD
    r3 = M.cost("image", "Black Forest Labs|FLUX 3 Image", 100)
    assert abs(r3["usd"] - 4.10) < 1e-6, r3


def test_compare_sorted_cheapest_first():
    import sys
    sys.path.insert(0, str(ROOT / "backend"))
    from app.web import media_cost as M

    rows = M.compare("image", 100)
    assert len(rows) >= 2
    prices = [r["usd"] for r in rows]
    assert prices == sorted(prices), "en ucuzdan pahaliya sirali degil"


def test_unknown_model_returns_none():
    import sys
    sys.path.insert(0, str(ROOT / "backend"))
    from app.web import media_cost as M

    assert M.cost("tts", "olmayan|model", 1000) is None


def test_route_registered():
    s = (ROOT / "backend" / "app" / "web" / "routes.py").read_text(encoding="utf-8")
    assert "/hesaplayici/ses-maliyeti" in s
    assert "media_cost" in s


def test_page_in_export_and_sitemap():
    e = (ROOT / "scripts" / "export_static.py").read_text(encoding="utf-8")
    r = (ROOT / "backend" / "app" / "web" / "routes.py").read_text(encoding="utf-8")
    assert "/hesaplayici/ses-maliyeti" in e, "export listesinde yok"
    assert "/hesaplayici/ses-maliyeti" in r, "sitemap'te yok"


def test_nav_link_present():
    b = (ROOT / "backend" / "app" / "web" / "templates" / "base.html").read_text(encoding="utf-8")
    assert "ses-maliyeti" in b, "navigasyonda link yok"