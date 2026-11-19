"""11. tur: canli sitede bulunan gercek hatalar + trafik altyapisi.

Bulunanlar (19.11.2026):
  1. Ham Jinja sizintisi: model sayfasinda "{{ primary.name }}" METIN olarak cikiyordu.
  2. API celiskisi: robots "Allow: /api/v1/" derken X-Robots-Tag "noindex" idi.
  3. Sitemap tutarsizligi: 61 karsilastirma sayfasi varken sitemap 22 gosteriyordu.
  4. RSS beslemesi yoktu (dagitim kanali eksik).
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

DIST = ROOT / "dist"
TPLS = ROOT / "backend" / "app" / "web" / "templates"
ROUTES = ROOT / "backend" / "app" / "web" / "routes.py"
EXPORT = ROOT / "scripts" / "export_static.py"


# ------------------------------------------------------------------ HATA-1
def test_no_nested_jinja_in_templates():
    """Sablonlarda ic ice {{ }} olmamali (ham metin olarak cikiyor)."""
    bad = []
    for f in TPLS.rglob("*.html"):
        src = f.read_text(encoding="utf-8", errors="ignore")
        for m in re.finditer(r"\{\{[^}]*\{\{", src):
            bad.append((f.name, m.group(0)[:50]))
    assert not bad, f"ic ice Jinja: {bad[:5]}"


@pytest.mark.skipif(not DIST.exists(), reason="dist/ yok")
def test_no_raw_jinja_in_built_html():
    """Uretilen HTML'de ham {{ ... }} kalmamali."""
    bad = []
    for f in DIST.rglob("*.html"):
        html = f.read_text(encoding="utf-8", errors="ignore")
        for m in re.finditer(r"\{\{[^}]{0,60}\}\}", html):
            bad.append((f.parent.relative_to(DIST).as_posix(), m.group(0)[:40]))
    assert not bad, f"ham Jinja: {bad[:5]}"


# ------------------------------------------------------------------ HATA-2
def test_api_headers_not_noindex():
    """robots.txt 'Allow: /api/v1/' diyorsa X-Robots-Tag noindex OLMAMALI."""
    src = EXPORT.read_text(encoding="utf-8")
    # Yalnizca /api/v1/* blogunun KENDI satirlari (sonraki uc basligina kadar).
    i = src.index('"/api/v1/*"')
    rest = src[i + len('"/api/v1/*"'):]
    block = rest.split('"/api/', 1)[0]
    assert "noindex" not in block.lower(), "API hala noindex (robots ile celisiyor)"


def test_write_endpoints_still_noindex():
    """Form/yazma uclari noindex olarak kalmali."""
    src = EXPORT.read_text(encoding="utf-8")
    for ep in ("/api/uyari", "/api/bulten", "/api/bulten-onay"):
        i = src.index(f'"{ep}"')
        assert "noindex" in src[i:i + 160].lower(), f"{ep} noindex degil"


@pytest.mark.skipif(not DIST.exists(), reason="dist/ yok")
def test_built_api_header_block():
    hdr = (DIST / "_headers").read_text(encoding="utf-8")
    i = hdr.index("/api/v1/*")
    assert "noindex" not in hdr[i:i + 100].lower()


# ------------------------------------------------------------------ HATA-3
def test_comparison_pairs_single_source():
    """Sitemap ve export AYNI cift listesini kullanmali."""
    routes = ROUTES.read_text(encoding="utf-8")
    export = EXPORT.read_text(encoding="utf-8")
    assert "compare_pairs" in routes, "routes.py tek kaynagi kullanmiyor"
    assert "compare_pairs" in export, "export_static.py tek kaynagi kullanmiyor"


def test_comparison_pairs_are_meaningful():
    from app.web.compare_pairs import MAX_PAIRS, PREFERRED_PAIRS, comparison_pairs

    assert len(PREFERRED_PAIRS) >= 15, "elle secilmis cift az"
    assert MAX_PAIRS >= 50, "cift siniri dusuk"
    pairs = comparison_pairs([], is_indexable=lambda r: False)
    assert pairs == [], "bos havuzda cift uretmemeli"


@pytest.mark.skipif(not DIST.exists(), reason="dist/ yok")
def test_sitemap_matches_disk_comparisons():
    """Sitemap'teki karsilastirmalar disktekiyle ayni olmali."""
    sm = (DIST / "sitemap.xml").read_text(encoding="utf-8")
    on_disk = sorted(
        p.name for p in (DIST / "karsilastir").iterdir() if (p / "index.html").exists()
    )
    missing = [s for s in on_disk if s not in sm]
    assert not missing, f"sitemap'te eksik karsilastirma: {missing[:5]}"


# ------------------------------------------------------------------ HATA-4
def test_rss_feed_exists():
    assert '@router.get("/rss.xml"' in ROUTES.read_text(encoding="utf-8")


@pytest.mark.skipif(not DIST.exists(), reason="dist/ yok")
def test_rss_is_valid_xml():
    import xml.etree.ElementTree as ET

    p = DIST / "rss.xml"
    assert p.exists(), "rss.xml uretilmemis"
    tree = ET.parse(p)
    root = tree.getroot()
    assert root.tag == "rss"
    items = root.findall("./channel/item")
    assert len(items) >= 5, f"RSS item az: {len(items)}"
    for it in items[:3]:
        assert it.findtext("title")
        assert it.findtext("link", "").startswith("https://tokenmaliyet.com/")


@pytest.mark.skipif(not DIST.exists(), reason="dist/ yok")
def test_rss_is_autodiscovered():
    """Sayfalarda RSS otodiscovery etiketi olmali."""
    html = (DIST / "fiyatlar" / "index.html").read_text(encoding="utf-8", errors="ignore")
    assert 'type="application/rss+xml"' in html
    assert '/rss.xml' in html
