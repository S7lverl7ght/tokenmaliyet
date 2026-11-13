"""6. tur denetim raporu regresyon testleri (13.11.2026).

Her test, raporun somut bir iddiasini kilitler. Boylece ayni hata
tekrar etmeye calisirsa CI kirmizi olur.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TPL = ROOT / "backend" / "app" / "web" / "templates"


def read(p):
    return p.read_text(encoding="utf-8")


# ---------- HATA-1: PAT sizintisi ----------

def test_no_hardcoded_pat_in_project():
    """Depoda acik metin GitHub PAT bulunmamali."""
    skip = {".git", ".venv", "__pycache__", "dist", ".pgdata", "node_modules"}
    offenders = []
    for path in ROOT.rglob("*"):
        if any(part in skip for part in path.parts):
            continue
        if not path.is_file() or path.suffix not in {".py", ".js", ".json", ".yml", ".yaml", ".toml"}:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if re.search(r"ghp_[A-Za-z0-9]{20,}", text):
            offenders.append(str(path.relative_to(ROOT)))
    assert not offenders, f"PAT sizintisi: {offenders}"


# ---------- HATA-2 / HATA-3 / SEO-5: sitemap ----------

def test_sitemap_includes_calculator():
    s = read(ROOT / "backend" / "app" / "web" / "routes.py")
    seg = s[s.index("def sitemap"):]
    seg = seg[:seg.index("return Response")]
    assert '"/hesaplayici"' in seg, "/hesaplayici sitemap'te yok"


def test_sitemap_has_lastmod():
    s = read(ROOT / "backend" / "app" / "web" / "routes.py")
    seg = s[s.index("def sitemap"):]
    assert "<lastmod>" in seg, "lastmod basilmiyor"


def test_sitemap_includes_english_variants():
    s = read(ROOT / "backend" / "app" / "web" / "routes.py")
    seg = s[s.index("def sitemap"):]
    seg = seg[:seg.index("return Response")]
    assert "/en/fiyatlar" in seg and "/en/hesaplayici" in seg


# ---------- HATA-4: og:image ----------

def test_og_image_meta_present():
    b = read(TPL / "base.html")
    assert 'property="og:image"' in b
    assert 'name="twitter:image"' in b
    assert "summary_large_image" in b


def test_og_image_file_exists_and_sized():
    p = ROOT / "backend" / "app" / "web" / "static" / "og-image.png"
    assert p.exists(), "og-image.png yok"
    assert p.stat().st_size > 5000, "og-image cok kucuk"
    # PNG boyutu: IHDR'dan genislik/yukseklik
    data = p.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    w = int.from_bytes(data[16:20], "big")
    h = int.from_bytes(data[20:24], "big")
    assert (w, h) == (1200, 630), f"beklenen 1200x630, bulunan {w}x{h}"


# ---------- HATA-5: tema tooltip ----------

def test_theme_toggle_title_is_not_language():
    b = read(TPL / "base.html")
    for line in b.splitlines():
        if "theme-toggle" in line and "<button" in line:
            assert "common.language" not in line, "tema butonu yanlis tooltip"
            assert "theme.toggle" in line
            break
    else:
        raise AssertionError("theme-toggle butonu bulunamadi")


# ---------- HATA-6: tek arama kutusu ----------

def test_single_search_input():
    p = read(TPL / "prices.html")
    assert 'id="q"' in p, "arama kutusu yok"
    assert 'id="live-q"' not in p, "ikinci arama kutusu hala var"


def test_search_js_uses_q_and_index():
    p = read(TPL / "prices.html")
    assert 'getElementById("q")' in p
    assert "models-index.json" in p


# ---------- HATA-7: gercek 301 ----------

def test_export_writes_redirects_file():
    s = read(ROOT / "scripts" / "export_static.py")
    assert '"_redirects"' in s, "_redirects uretilmiyor"
    assert "/hesaplayici/" in s and "301" in s
