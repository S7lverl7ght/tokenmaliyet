"""Statik cikti izolasyonu testi (rapor 4. tur bolum 6)."""
from __future__ import annotations

import re
from pathlib import Path

import pytest

DIST = Path(__file__).resolve().parents[1] / "dist"

FORBIDDEN = [
    "ADMIN_TOKEN",
    "DATABASE_URL",
    "postgresql+psycopg",
    "Traceback (most recent call last)",
    "/admin/kuyruk",
    "GizliAnahtar",
]


@pytest.mark.skipif(not DIST.exists(), reason="dist/ yok (export_static.py calistirilmadi)")
def test_no_secrets_or_admin_in_dist():
    """dist/ asla sir, admin rotasi veya stack trace icermemeli."""
    leaks: list[str] = []
    for path in DIST.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix not in {".html", ".txt", ".xml", ".css", ".js", ".json"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for needle in FORBIDDEN:
            if needle in text:
                leaks.append(f"{path.relative_to(DIST)}: {needle}")
    assert not leaks, "statik ciktida sizinti: " + "; ".join(leaks[:5])


@pytest.mark.skipif(not DIST.exists(), reason="dist/ yok")
def test_dist_has_security_headers():
    headers = DIST / "_headers"
    assert headers.exists(), "_headers dosyasi yok"
    body = headers.read_text(encoding="utf-8")
    for header in ("X-Frame-Options", "Content-Security-Policy", "Strict-Transport-Security",
                   "X-Content-Type-Options", "Referrer-Policy"):
        assert header in body, f"{header} eksik"


@pytest.mark.skipif(not DIST.exists(), reason="dist/ yok")
def test_static_pages_contain_data():
    """Veri HTML icinde olmali (JS'siz okunabilir) — raporun SEO itirazi."""
    prices = DIST / "fiyatlar" / "index.html"
    assert prices.exists()
    body = prices.read_text(encoding="utf-8")
    assert re.search(r'class="name"', body), "model satiri yok"
    assert "USD" in body


@pytest.mark.skipif(not DIST.exists(), reason="dist/ yok")
def test_static_flag_present():
    """Statik sayfalarda window.__STATIC__ bayragi olmali (JS filtre icin)."""
    page = DIST / "fiyatlar" / "index.html"
    assert "__STATIC__" in page.read_text(encoding="utf-8")


@pytest.mark.skipif(not DIST.exists(), reason="dist/ yok")
def test_no_noindex_on_sitemap_pages_in_dist():
    """dist/'te sitemap'e giren sayfalar noindex olmamali.

    Gercek hata (12.11.2026): 22 URL sitemap'te olup noindex idi; GPU detay
    sayfalari ayrica ana sayfanin canonical'ini gosteriyordu.
    """
    import re
    sm = (DIST / "sitemap.xml").read_text(encoding="utf-8")
    locs = re.findall(r"<loc>https://tokenmaliyet\.com([^<]*)</loc>", sm)
    bad = []
    for path in locs:
        if not path or path == "/":
            f = DIST / "index.html"
        else:
            f = DIST / path.strip("/") / "index.html"
        if not f.exists():
            bad.append((path, "dosya yok"))
            continue
        html = f.read_text(encoding="utf-8", errors="ignore")
        if 'content="noindex' in html:
            bad.append((path, "noindex"))
    assert not bad, f"sitemap sayfasi indekslenemez: {bad[:6]}"


@pytest.mark.skipif(not DIST.exists(), reason="dist/ yok")
def test_gpu_detail_canonical_is_self():
    """GPU detay sayfalari kendi canonical'ini gostermeli."""
    import re
    for d in sorted((DIST / "gpu").glob("*/index.html"))[:5]:
        html = d.read_text(encoding="utf-8", errors="ignore")
        m = re.search(r'<link rel="canonical" href="([^"]+)"', html)
        assert m, f"{d}: canonical yok"
        expected = "/gpu/" + d.parent.name
        assert m.group(1).endswith(expected), f"{d.parent.name}: {m.group(1)}"
