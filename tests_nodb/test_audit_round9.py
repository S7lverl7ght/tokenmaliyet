"""9. tur denetimi: canli sitede bulunan gercek hatalarin regresyon testleri.

Bu testlerin hepsi 15.11.2026 tarihli CANLI kontrol sirasinda bulunan gercek
hatalari kilitler. Amac: ayni hata bir daha sessizce geri gelmesin.
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

# --------------------------------------------------------------------------
# 10. tur: API erisimi, /docs ve bulten
# --------------------------------------------------------------------------

def test_robots_does_not_block_api():
    """/api/ robots ile ENGELLENMEMELI.

    Site ucretsiz JSON API vaat ediyor ve API sayfasi buna baglanti veriyor;
    robots ile engellemek bu vaatle celisir.
    """
    src = (ROOT / "backend" / "app" / "web" / "routes.py").read_text(encoding="utf-8")
    robots = src[src.index('def robots():'):]
    robots = robots[: robots.index("def ", robots.index("return"))] if "def " in robots[10:] else robots
    assert '"Disallow: /api/"' not in robots, "robots hala /api/ dosyasini engelliyor"
    assert "Allow: /api/v1/" in robots, "API uclari icin Allow kurali yok"
    # Form uclari (yazma islemi, indekslenebilir icerik yok) kapali kalmali.
    assert "Disallow: /api/bulten" in robots
    assert "Disallow: /admin" in robots


def test_api_docs_page_exists():
    """Kullanicinin gordugu API dokumantasyonu gercekten var olmali."""
    assert (ROOT / "backend" / "app" / "web" / "templates" / "api_docs.html").exists()
    src = (ROOT / "backend" / "app" / "web" / "routes.py").read_text(encoding="utf-8")
    assert '@router.get("/api-dokumantasyon"' in src
    assert '@router.get("/docs"' in src, "/docs yonlendirmesi yok"


def test_footer_links_to_real_api_page():
    """/docs olu baglantisi yerine gercek sayfaya baglanti verilmeli."""
    base = (ROOT / "backend" / "app" / "web" / "templates" / "base.html").read_text(encoding="utf-8")
    assert 'href="/api-dokumantasyon"' in base
    about = (ROOT / "backend" / "app" / "web" / "templates" / "about.html").read_text(encoding="utf-8")
    assert 'href="/api-dokumantasyon"' in about


def test_newsletter_form_in_calculator():
    """Hesaplayicida e-posta toplama formu olmali."""
    calc = (ROOT / "backend" / "app" / "web" / "templates" / "calculator.html").read_text(encoding="utf-8")
    assert 'id="bultenForm"' in calc
    assert 'action="/api/bulten"' in calc
    # Cift onay: onay kutusu zorunlu
    assert 'name="consent"' in calc
    # Bot korumasi
    assert "cf-turnstile" in calc


def test_newsletter_endpoints_exist():
    fn = ROOT / "functions" / "api"
    for name in ("bulten.js", "bulten-onay.js", "bulten-iptal.js"):
        assert (fn / name).exists(), f"{name} yok"
    body = (fn / "bulten.js").read_text(encoding="utf-8")
    # Cift onay: onaylanmamis kayit confirmed=0 ile yazilir
    assert "confirmed, confirm_token" in body or "(email, lang, confirmed" in body
    assert "verifyTurnstile" in body, "bot korumasi yok"
    assert "honeypot" in body or "website" in body, "bal kupu yok"


def test_newsletter_schema_has_consent_fields():
    sql = (ROOT / "db" / "newsletter.sql").read_text(encoding="utf-8")
    for col in ("email", "confirmed", "confirm_token", "unsubscribe_token",
                "consent_at", "unsubscribed_at", "ip_hash"):
        assert col in sql, f"semada {col} yok"


def test_canonical_and_og_are_same_url():
    """canonical ile og:url ayni olmali ve sayfanin kendisini gostermeli."""
    if not DIST.exists():
        pytest.skip("dist/ yok")
    bad = []
    for f in DIST.rglob("index.html"):
        rel = f.parent.relative_to(DIST).as_posix()
        if rel == ".":
            continue
        html = f.read_text(encoding="utf-8", errors="ignore")
        c = re.search(r'<link rel="canonical" href="([^"]*)"', html)
        o = re.search(r'<meta property="og:url" content="([^"]*)"', html)
        if not c:
            bad.append((rel, "canonical yok"))
            continue
        if c.group(1) != f"/{rel}/" and not c.group(1).endswith(f"/{rel}/"):
            bad.append((rel, c.group(1)))
        if o and o.group(1).strip() and o.group(1) != c.group(1):
            bad.append((rel, "og!=canonical"))
    assert not bad, f"kanonik/og sorunu: {bad[:6]}"

# --------------------------------------------------------------------------
# HATA 11: JSON-LD bozuktu -> Google Search Console "Yanlis deger turu"
#
# Kok neden: Jinja'da '|' filtresi '~' operantorunden ONCE baglar. prices.html'de
#   {{ ('AI API fiyatlari — ' ~ total ~ ' model' | tojson) }}
# yalnizca ' model' parcasini JSON'a ceviriyordu ve cikti soyle bozuluyordu:
#   "name":AI API fiyatlari — 452" model",
# Bu yuzden /fiyatlar'da Dataset yapisi gecersizdi ve Google zengin sonucu
# kaldirdi (Search Console: "Ayristirilamayan yapilandirilmis veri").
# --------------------------------------------------------------------------

def test_all_jsonld_blocks_are_valid_json():
    """Her JSON-LD blogu gecerli JSON olmali."""
    if not DIST.exists():
        pytest.skip("dist/ yok")
    bad = []
    total = 0
    for f in DIST.rglob("*.html"):
        html = f.read_text(encoding="utf-8", errors="ignore")
        for m in re.finditer(r'<script type="application/ld\+json">([\s\S]*?)</script>', html):
            total += 1
            try:
                json.loads(m.group(1))
            except Exception as exc:
                bad.append((f.parent.relative_to(DIST).as_posix(), str(exc)[:60]))
    assert total > 0
    assert not bad, f"gecersiz JSON-LD: {bad[:5]}"


def test_prices_dataset_name_is_string():
    """Dataset 'name' bir JSON string olmali (Jinja oncelik hatasi geri gelmesin)."""
    if not DIST.exists():
        pytest.skip("dist/ yok")
    for rel in ("fiyatlar", "try/fiyatlar", "en/fiyatlar", "en/try/fiyatlar"):
        p = DIST / rel / "index.html"
        if not p.exists():
            continue
        html = p.read_text(encoding="utf-8", errors="ignore")
        blocks = re.findall(r'<script type="application/ld\+json">([\s\S]*?)</script>', html)
        datasets = [json.loads(b) for b in blocks]
        ds = next((d for d in datasets if d.get("@type") == "Dataset"), None)
        assert ds is not None, f"{rel}: Dataset yok"
        assert isinstance(ds.get("name"), str), f"{rel}: name string degil"
        assert "AI API" in ds["name"]


def test_jsonld_urls_are_directory_style():
    """JSON-LD icindeki site adresleri de / ile bitmeli (308 zinciri olmesin)."""
    if not DIST.exists():
        pytest.skip("dist/ yok")
    base = "https://tokenmaliyet.com"
    bad = []
    for f in DIST.rglob("*.html"):
        html = f.read_text(encoding="utf-8", errors="ignore")
        for m in re.finditer(r'<script type="application/ld\+json">([\s\S]*?)</script>', html):
            try:
                data = json.loads(m.group(1))
            except Exception:
                continue

            def walk(o):
                if isinstance(o, dict):
                    for k, v in o.items():
                        if k in ("url", "item", "@id", "contentUrl") and isinstance(v, str) \
                                and v.startswith(base):
                            path = v[len(base):].split("?")[0]
                            last = path.rsplit("/", 1)[-1] if path else ""
                            if path and not path.endswith("/") and "." not in last:
                                bad.append((f.parent.relative_to(DIST).as_posix(), v))
                        else:
                            walk(v)
                elif isinstance(o, list):
                    for v in o:
                        walk(v)

            walk(data)
    assert not bad, f"JSON-LD adresi / ile bitmiyor: {bad[:5]}"


def test_dataset_url_matches_canonical():
    """Dataset.url sayfanin kanonik adresiyle ayni olmali."""
    if not DIST.exists():
        pytest.skip("dist/ yok")
    p = DIST / "fiyatlar" / "index.html"
    if not p.exists():
        pytest.skip("fiyatlar yok")
    html = p.read_text(encoding="utf-8", errors="ignore")
    canon = re.search(r'<link rel="canonical" href="([^"]*)"', html).group(1)
    blocks = re.findall(r'<script type="application/ld\+json">([\s\S]*?)</script>', html)
    ds = next(d for d in (json.loads(b) for b in blocks) if d.get("@type") == "Dataset")
    assert ds["url"] == canon, f"Dataset.url {ds['url']} != canonical {canon}"

# --------------------------------------------------------------------------
# HATA 12: EN sayfalarda ASCII-only Turkce kelimeler (16.11.2026, CI'da yakalandi)
#
# Onceki testler yalnizca Turkce'ye ozgu HARFLERI (ç, ğ, ı...) ariyordu. Bu yuzden
# "Pazaryeri", "Dogrudan API", "Temizle", "Fiyatlar" gibi ASCII ile yazilan
# Turkce kelimeler gozden kacti. Gercek hata: /en/fiyatlar tablosunda kanal
# etiketi "Pazaryeri" gorunuyordu; /en/fiyatlar'da tazelik rozeti "güncel" idi.
# --------------------------------------------------------------------------

# Turkce'ye ozgu harf icermeyen ama Ingilizce metinde asla gecmeyen kelimeler.
ASCII_TURKISH = [
    "Pazaryeri", "Dogrudan", "Girdi", "Cikti", "Fiyat", "Fiyatlar",
    "Temizle", "Hesapla", "Hesaplayici", "Kaynak", "Saglayici",
    "Sayfa yolu", "Filtreler", "Guncelle", "Toplam", "Seciniz",
    "Tum modeller", "Onaylandi", "Bilinmiyor", "Dogrulandi",
]


def _visible_text(html: str) -> str:
    """Etiketleri ve scriptleri atar; kullaniciya gorunen metni dondurur."""
    t = re.sub(r"<script[\s\S]*?</script>", " ", html)
    t = re.sub(r"<style[\s\S]*?</style>", " ", t)
    t = re.sub(r"<!--[\s\S]*?-->", " ", t)
    t = re.sub(r"<[^>]+>", " ", t)
    t = re.sub(r"&[a-z]+;", " ", t)
    return re.sub(r"\s+", " ", t)


def test_english_pages_have_no_ascii_turkish_words():
    """EN sayfalarda ASCII ile yazilmis Turkce kelime de olmamali."""
    if not DIST.exists():
        pytest.skip("dist/ yok")
    bad = []
    for f in sorted((DIST / "en").rglob("index.html")):
        text = _visible_text(f.read_text(encoding="utf-8", errors="ignore"))
        hits = [w for w in ASCII_TURKISH if w in text]
        if hits:
            bad.append((f.parent.relative_to(DIST).as_posix(), hits))
    assert not bad, f"EN sayfada Turkce kelime: {bad[:6]}"


def test_english_attribute_labels_are_localised():
    """aria-label / placeholder gibi gorunur etiketler de cevrilmeli."""
    if not DIST.exists():
        pytest.skip("dist/ yok")
    bad = []
    for f in sorted((DIST / "en").rglob("index.html")):
        html = f.read_text(encoding="utf-8", errors="ignore")
        for attr in re.findall(r'(?:aria-label|placeholder|title|alt)="([^"]*)"', html):
            if any(w in attr for w in ASCII_TURKISH):
                bad.append((f.parent.relative_to(DIST).as_posix(), attr[:50]))
    assert not bad, f"EN sayfada Turkce etiket: {bad[:6]}"


def test_freshness_badge_is_language_aware():
    """Tazelik rozeti dile gore etiket uretmeli (sabit Turkce olmamali)."""
    from app.web.render import freshness_badge

    import datetime as _dt

    now = _dt.datetime.now(_dt.timezone.utc)
    tr = freshness_badge(now, "tr")
    en = freshness_badge(now, "en")
    assert tr["label"] != en["label"], "rozet dili degismiyor"
    assert tr["label"] == "güncel"
    assert en["label"] == "current"
    # Geriye donuk uyum: dil verilmezse Turkce
    assert freshness_badge(now)["label"] == "güncel"


def test_channel_labels_are_language_aware():
    """Kanal etiketleri (Pazaryeri/Marketplace) dile gore secilmeli."""
    from app.web.render import CHANNEL_LABELS, CHANNEL_LABELS_EN

    assert CHANNEL_LABELS["marketplace"] == "Pazaryeri"
    assert CHANNEL_LABELS_EN["marketplace"] == "Marketplace"
    src = (ROOT / "backend" / "app" / "web" / "render.py").read_text(encoding="utf-8")
    assert '"channel_labels": CHANNEL_LABELS_EN if lang == "en" else CHANNEL_LABELS' in src
