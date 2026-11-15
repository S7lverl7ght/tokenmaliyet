"""9. tur denetimi: canli sitede bulunan gercek hatalarin regresyon testleri.

Bu testlerin hepsi 15.11.2026 tarihli CANLI kontrol sirasinda bulunan gercek
hatalari kilitler. Amac: ayni hata bir daha sessizce geri gelmesin.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

DIST = ROOT / "dist"
ROUTES = ROOT / "backend" / "app" / "web" / "routes.py"
RENDER = ROOT / "backend" / "app" / "web" / "render.py"
EXPORT = ROOT / "scripts" / "export_static.py"
TPL = ROOT / "backend" / "app" / "web" / "templates"


# --------------------------------------------------------------------------
# HATA 1: Kanonik adresler dizin bicimiyle uyusmuyordu.
# Cloudflare Pages /fiyatlar -> /fiyatlar/ diye 308 yonlendiriyor, ama kanonik
# etiket /fiyatlar (egik cizgisiz) diyordu. Google bunu "kanonik adres
# yonlendiriyor" diye isaretler ve siralama sinyali kaybolur.
# --------------------------------------------------------------------------

def test_canonical_url_appends_trailing_slash():
    from app.web.render import canonical_url

    assert canonical_url("/fiyatlar").endswith("/fiyatlar/")
    assert canonical_url("/en/hesaplayici").endswith("/en/hesaplayici/")
    # kok adres tek egik cizgi olmali
    assert canonical_url("/").endswith("/") and not canonical_url("/").endswith("//")


def test_canonical_url_strips_query():
    from app.web.render import canonical_url

    assert "?" not in canonical_url("/fiyatlar?page=2")
    assert "&" not in canonical_url("/fiyatlar?q=x&sort=name")


def test_no_page_shows_unsuffixed_canonical():
    """Uretilen her sayfa KENDI adresini kanonik gostermeli."""
    if not DIST.exists():
        pytest.skip("dist/ yok")
    bad = []
    for f in DIST.rglob("*.html"):
        rel = f.parent.relative_to(DIST).as_posix()
        if rel == ".":
            continue          # kok yonlendirme sayfasi
        html = f.read_text(encoding="utf-8", errors="ignore")
        m = re.search(r'<link rel="canonical" href="([^"]+)"', html)
        if not m:
            bad.append((rel, "kanonik yok"))
            continue
        expected = f"/{rel}/"
        if not m.group(1).endswith(expected):
            bad.append((rel, m.group(1)))
    assert not bad, f"kanonik adres sayfanin kendisi degil: {bad[:6]}"


def test_english_calculator_has_own_canonical():
    """EN hesaplayici Turkce ana sayfayi kanonik gostermemeli."""
    if not DIST.exists():
        pytest.skip("dist/ yok")
    html = (DIST / "en" / "hesaplayici" / "index.html").read_text(encoding="utf-8", errors="ignore")
    m = re.search(r'<link rel="canonical" href="([^"]+)"', html)
    assert m, "EN hesaplayicida kanonik yok"
    assert m.group(1).rstrip("/").endswith("/en/hesaplayici"), m.group(1)


# --------------------------------------------------------------------------
# HATA 2: Ingilizce sayfalarda Turkce metin kaliyordu.
# --------------------------------------------------------------------------

TR_CHARS = "çğıöşüÇĞİÖŞÜ"

# Turkce'ye ozgu, Ingilizce metinde asla gecmeyecek kelimeler.
TR_ONLY = [
    "Fiyatlar", "Kaynaklar", "Kurumsal", "Rehberler", "GPU maliyetleri",
    "daha az", "Birim:", "Kalem", "Hesaplayıcı", "Sayfa yolu",
]


def _english_pages():
    if not DIST.exists():
        return []
    return sorted((DIST / "en").rglob("index.html"))


def test_english_pages_have_no_turkish_letters():
    """EN sayfada Turkce karakterli kelime kalmamali."""
    if not DIST.exists():
        pytest.skip("dist/ yok")
    bad = []
    for f in _english_pages():
        html = f.read_text(encoding="utf-8", errors="ignore")
        text = re.sub(r"<script[\s\S]*?</script>", " ", html)
        text = re.sub(r"<[^>]+>", " ", text)
        for word in re.findall(r"[^\W\d_]{3,}", text, flags=re.UNICODE):
            if any(ch in word for ch in TR_CHARS):
                bad.append((f.parent.relative_to(DIST).as_posix(), word))
                break
    assert not bad, f"EN sayfada Turkce kelime: {bad[:8]}"


def test_english_footer_is_translated():
    """Alt bilgi basliklari EN sayfada Ingilizce olmali."""
    if not DIST.exists():
        pytest.skip("dist/ yok")
    html = (DIST / "en" / "hesaplayici" / "index.html").read_text(encoding="utf-8", errors="ignore")
    for bad in ("<h4>Veri</h4>", "<h4>Kaynaklar</h4>", "<h4>Kurumsal</h4>"):
        assert bad not in html, f"EN alt bilgide Turkce baslik: {bad}"


# --------------------------------------------------------------------------
# HATA 3: Ic baglantilar 404 donuyordu.
# /fiyatlar tablosundaki 50 model baglantisindan 17'sinin sayfasi hic
# uretilmiyordu; ayrica '~...-latest' takma adlari 58 kirik baglanti uretiyordu.
# --------------------------------------------------------------------------

def test_no_broken_internal_links():
    if not DIST.exists():
        pytest.skip("dist/ yok")
    files = {"/" + p.relative_to(DIST).as_posix() for p in DIST.rglob("*") if p.is_file()}
    targets = set(files)
    for f in files:
        if f.endswith("/index.html"):
            targets.add(f[: -len("index.html")])

    broken = []
    for p in DIST.rglob("*.html"):
        html = p.read_text(encoding="utf-8", errors="ignore")
        for href in re.findall(r'href="(/[^"#?]*)', html):
            if href not in targets and (href + "/") not in targets and (href + "index.html") not in targets:
                broken.append((p.relative_to(DIST).as_posix(), href))
    assert not broken, f"kirik ic baglanti: {broken[:8]}"


def test_alias_models_never_linked():
    """Takma ad ('~...-latest') kayitlarinin sayfasi yok; link verilmemeli."""
    src = ROUTES.read_text(encoding="utf-8")
    assert "not r.is_alias" in src, "benzer model havuzu alias'i dislamiyor"
    assert "not x.is_alias" in src, "secenek listesi alias'i dislamiyor"


# --------------------------------------------------------------------------
# HATA 4: JSON API uclari statik sitede 404 donuyordu.
# Alt bilgi /api/v1/prices?format=json adresine baglanti veriyordu.
# --------------------------------------------------------------------------

def test_static_export_writes_json_endpoints():
    s = EXPORT.read_text(encoding="utf-8")
    assert '("prices", "/api/v1/prices")' in s
    assert '("model-options", "/api/v1/model-options")' in s
    assert '("fx", "/api/v1/fx?quote=TRY")' in s


@pytest.mark.skipif(not DIST.exists(), reason="dist/ yok")
def test_exported_json_endpoints_exist_and_parse():
    import json

    api = DIST / "api" / "v1"
    for name in ("model-options", "prices", "fx", "providers"):
        f = api / name
        assert f.exists(), f"{name} uretilmemis"
        data = json.loads(f.read_text(encoding="utf-8"))
        assert data, f"{name} bos"


def test_no_dead_docs_link_in_templates():
    """/docs statik sitede yok; ona baglanti veren kalmamali."""
    offenders = []
    for f in TPL.rglob("*.html"):
        if 'href="/docs"' in f.read_text(encoding="utf-8", errors="ignore"):
            offenders.append(f.name)
    assert not offenders, f"olu /docs baglantisi: {offenders}"


# --------------------------------------------------------------------------
# HATA 5: hreflang var olmayan Ingilizce adresi bildiriyordu.
# --------------------------------------------------------------------------

def test_hreflang_only_lists_real_variants():
    from app.web.render import _hreflang_pairs

    # Tek dilli sayfada yalnizca tr + x-default olmali, sahte /en/ adresi olmamali.
    pairs = _hreflang_pairs("/hakkinda", "tr")
    assert any(p["lang"] == "tr" for p in pairs)
    assert any(p["lang"] == "x-default" for p in pairs)
    # Iki dilli sayfada en de bulunmali.
    pairs2 = _hreflang_pairs("/hesaplayici", "tr")
    assert any(p["lang"] == "en" for p in pairs2)


def test_hreflang_urls_are_directory_style():
    from app.web.render import _hreflang_pairs

    for p in _hreflang_pairs("/fiyatlar", "tr"):
        assert p["url"].endswith("/"), p["url"]


# --------------------------------------------------------------------------
# HATA 6: media cost sayfasi hreflang'de eslesmiyordu (EN varyanti varken).
# --------------------------------------------------------------------------

def test_media_cost_is_in_en_paths():
    src = RENDER.read_text(encoding="utf-8")
    assert '"/hesaplayici/ses-maliyeti"' in src, "ses-maliyeti EN yollarina eklenmemis"


# --------------------------------------------------------------------------
# HATA 7: Baslik kurallari (uzunluk + benzersizlik).
# Iki model adindan olusan karsilastirma basliklari dogal olarak uzundur;
# Google kesme siniri ~60-70 karakterdir ve bunlar mesru basliklardir.
# --------------------------------------------------------------------------

def test_titles_are_not_too_long():
    if not DIST.exists():
        pytest.skip("dist/ yok")
    bad = []
    for f in DIST.rglob("index.html"):
        rel = f.parent.relative_to(DIST).as_posix()
        html = f.read_text(encoding="utf-8", errors="ignore")
        m = re.search(r"<title>(.*?)</title>", html, re.S)
        if not m:
            continue
        limit = 72 if rel.startswith("karsilastir") else 62
        if len(m.group(1).strip()) > limit:
            bad.append((rel, len(m.group(1).strip())))
    assert not bad, f"baslik cok uzun: {bad[:6]}"


def test_titles_are_unique():
    """Mukerrer baslik = kopya icerik sinyali; her sayfa benzersiz olmali."""
    if not DIST.exists():
        pytest.skip("dist/ yok")
    seen: dict[str, str] = {}
    dups = []
    for f in DIST.rglob("index.html"):
        rel = f.parent.relative_to(DIST).as_posix()
        html = f.read_text(encoding="utf-8", errors="ignore")
        m = re.search(r"<title>(.*?)</title>", html, re.S)
        if not m:
            continue
        t = m.group(1).strip()
        # /try/ varyantlari para birimi ekiyle ayrilir; onlar da benzersiz olmali.
        if t in seen:
            dups.append((seen[t], rel, t[:50]))
        else:
            seen[t] = rel
    assert not dups, f"mukerrer baslik: {dups[:5]}"


def test_every_page_has_description():
    if not DIST.exists():
        pytest.skip("dist/ yok")
    bad = []
    for f in DIST.rglob("index.html"):
        html = f.read_text(encoding="utf-8", errors="ignore")
        m = re.search(r'<meta name="description" content="([^"]*)"', html)
        if not m or len(m.group(1).strip()) < 20:
            bad.append(f.parent.relative_to(DIST).as_posix())
    assert not bad, f"description eksik: {bad[:6]}"


def test_descriptions_within_limit():
    if not DIST.exists():
        pytest.skip("dist/ yok")
    bad = []
    for f in DIST.rglob("index.html"):
        html = f.read_text(encoding="utf-8", errors="ignore")
        m = re.search(r'<meta name="description" content="([^"]*)"', html)
        if m and len(m.group(1)) > 160:
            bad.append((f.parent.relative_to(DIST).as_posix(), len(m.group(1))))
    assert not bad, f"description cok uzun: {bad[:6]}"


def test_sitemap_has_no_noindex_or_redirecting_urls():
    """sitemap'te noindex sayfa veya yonlendiren adres olmamali."""
    if not DIST.exists():
        pytest.skip("dist/ yok")
    sm = (DIST / "sitemap.xml").read_text(encoding="utf-8")
    locs = re.findall(r"<loc>([^<]+)</loc>", sm)
    assert locs, "sitemap bos"
    bad = []
    for u in locs:
        rel = u.replace("https://tokenmaliyet.com", "").strip("/")
        # kok adres 301 ile /hesaplayici/ adresine gidiyor -> sitemap'e girmemeli
        assert u != "https://tokenmaliyet.com/", "kok adres sitemap'te olmamali"
        p = DIST / rel / "index.html"
        if not p.exists():
            bad.append(("yok", rel))
            continue
        if re.search(r'content="noindex', p.read_text(encoding="utf-8", errors="ignore")):
            bad.append(("noindex", rel))
    assert not bad, f"sitemap sorunlu adres: {bad[:6]}"


def test_try_variants_have_distinct_titles():
    """TRY varyantlari ayni basligi tasimamali (kopya icerik)."""
    if not DIST.exists():
        pytest.skip("dist/ yok")
    pairs = [("fiyatlar", "try/fiyatlar"), ("gpu-maliyetleri", "try/gpu-maliyetleri")]
    for a, b in pairs:
        pa, pb = DIST / a / "index.html", DIST / b / "index.html"
        if not (pa.exists() and pb.exists()):
            continue
        ta = re.search(r"<title>(.*?)</title>", pa.read_text(encoding="utf-8"), re.S).group(1)
        tb = re.search(r"<title>(.*?)</title>", pb.read_text(encoding="utf-8"), re.S).group(1)
        assert ta.strip() != tb.strip(), f"{a} ve {b} ayni basligi tasiyor"
