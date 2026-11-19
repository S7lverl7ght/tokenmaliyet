"""Herkese acik sayfalari statik HTML olarak disa aktarir.

Neden: inceleme raporu 3. tur "sayfalar JS ile ciziliyor olabilir, kaynak HTML'de veri
gorunmeli" dedi; ayrica Cloudflare Pages'te 0 maliyetle servis icin statik cikti gerekir.

Cikti: dist/ altinda <yol>/index.html + static/ kopyasi + sitemap.xml + robots.txt
"""
from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

DIST = ROOT / "dist"

# Statik export edilecek sayfalar (dinamik uclar haric)
PAGES = [
    ("/fiyatlar", "fiyatlar"),
    ("/karsilastir", "karsilastir"),
    ("/hesaplayici", "hesaplayici"),
    ("/hesaplayici/ses-maliyeti", "hesaplayici/ses-maliyeti"),
    ("/token-sayaci", "token-sayaci"),
    ("/turkce-token-maliyeti", "turkce-token-maliyeti"),
    ("/gpu-maliyetleri", "gpu-maliyetleri"),
    ("/degisiklikler", "degisiklikler"),
    ("/rehber", "rehber"),
    ("/hakkinda", "hakkinda"),
    ("/danismanlik", "danismanlik"),
    ("/gizlilik", "gizlilik"),
    ("/kullanim-kosullari", "kullanim-kosullari"),
    ("/api-dokumantasyon", "api-dokumantasyon"),
    ("/iletisim", "iletisim"),
    ("/duzeltmeler", "duzeltmeler"),
    ("/uyari", "uyari"),
]


def main() -> int:
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir(parents=True)

    written = 0
    for path, slug in PAGES:
        resp = client.get(path)
        if resp.status_code != 200:
            print(f"[skip] {path} -> {resp.status_code}")
            continue
        target = DIST / slug / "index.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        html = resp.text.replace(
            "<head>",
            '<head>\n<script>window.__STATIC__=true;</script>',
            1,
        )
        target.write_text(html, encoding="utf-8")
        written += 1
        print(f"[ok] {path} -> {target.relative_to(ROOT)}")

    # Rehber yazilari
    from app.web.content.guides import GUIDES

    for g in GUIDES:
        resp = client.get(f"/rehber/{g.slug}")
        if resp.status_code != 200:
            continue
        target = DIST / "rehber" / g.slug / "index.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(resp.text, encoding="utf-8")
        written += 1
        print(f"[ok] /rehber/{g.slug}")

    # Indekslenebilir model sayfalari
    from app.db import SessionLocal
    from app.web import default_models as dm
    from app.web import queries

    # KIRIK BAGLANTI KORUMASI (15.11.2026 canli testte bulundu):
    # /fiyatlar tablosunda 50 model baglantisi var ama yalnizca 44 sayfa uretiliyordu;
    # 17 baglanti 404 donuyordu. Artik ONCE indekslenebilir 60 model, SONRA tabloda
    # gorunen tum modeller (noindex) uretilir. Boylece statik sitede kirik link kalmaz.
    written_models: set[str] = set()
    with SessionLocal() as db:
        all_rows = queries.price_rows(db)
        # 1) indekslenebilir modeller (sitemap ile ayni kume)
        ordered = [r for r in all_rows if dm.is_indexable(r)][:60]
        # 2) tabloda gorunen geri kalan modeller (alias olmayanlar), sayfa 404 vermesin
        ordered += [r for r in all_rows if not dm.is_indexable(r) and not r.is_alias]

        for row in ordered:
            key = f"{row.provider_slug}/{row.slug}"
            if key in written_models:
                continue
            resp = client.get(f"/modeller/{row.provider_slug}/{row.slug}")
            if resp.status_code != 200:
                continue
            target = DIST / "modeller" / row.provider_slug / row.slug / "index.html"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(resp.text, encoding="utf-8")
            written_models.add(key)

    print(f"[ok] {len(written_models)} model sayfasi uretildi"
          f" (indekslenebilir: {sum(1 for r in ordered if dm.is_indexable(r))})")

    # Programatik GPU detay sayfalari (rapor 4. tur bolum 4: /gpu/<slug>)
    # Onemli: bu sayfalar KENDI canonical'ini ve index iznini almali.
    # Onceki hata: filtre parametresi kullanildigi icin noindex kaliyordu ve
    # canonical ana GPU sayfasini gosteriyordu (Search Console "noindex" hatasi).
    from app.db import SessionLocal as _SL
    from app.models import GpuPrice as _GP

    with _SL() as gdb:
        fams = {f.gpu_family for f in gdb.query(_GP).filter(_GP.status == "approved").all()}
    for fam in sorted(fams):
        slug = fam.lower().replace(" ", "-")
        resp = client.get(f"/gpu-maliyetleri?family={fam}")
        if resp.status_code != 200:
            continue
        html = resp.text.replace("<head>", '<head>\n<script>window.__STATIC__=true;</script>', 1)
        # robots: indekslenebilir
        html = html.replace(
            '<meta name="robots" content="noindex,nofollow">',
            '<meta name="robots" content="index,follow,max-image-preview:large">',
            1,
        )
        # SEO: her GPU sayfasi KENDI basligini almali.
        # Onceki hata: 44 GPU sayfasi ayni <title> ile cikiyordu (kopya icerik).
        import re as _re

        fam_title = f"{fam} GPU fiyatlari — saatlik kiralama | TokenMaliyet"
        fam_desc = (
            f"{fam} GPU kiralama fiyatlari: Runpod, Vast.ai, DataCrunch, Lambda ve "
            f"Hyperstack saatlik ucretleri, kaynak baglantisiyla."
        )[:155]
        html = _re.sub(r"<title>.*?</title>", f"<title>{fam_title}</title>", html, count=1, flags=_re.S)
        html = _re.sub(r'<meta name="description" content="[^"]*">',
                       f'<meta name="description" content="{fam_desc}">', html, count=1)
        html = _re.sub(r'<meta property="og:title" content="[^"]*">',
                       f'<meta property="og:title" content="{fam_title}">', html, count=1)
        html = _re.sub(r'<meta property="og:description" content="[^"]*">',
                       f'<meta property="og:description" content="{fam_desc}">', html, count=1)
        html = _re.sub(r"<h1[^>]*>GPU kiralama maliyetleri</h1>",
                       f"<h1>{fam} GPU kiralama fiyatlari</h1>", html, count=1)
        target = DIST / "gpu" / slug / "index.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(html, encoding="utf-8")
        print(f"[ok] /gpu/{slug}")

    # Programatik karsilastirma sayfalari (rapor 4. tur: populer 20 cift)
    from app.db import SessionLocal as _SL2
    from app.web import default_models as _dm
    from app.web import queries as _q

    # --- Karsilastirma ciftleri (TEK kaynak: app.web.compare_pairs) ---
    from app.web.compare_pairs import comparison_pairs

    with _SL2() as db2:
        pair_rows = comparison_pairs(_q.price_rows(db2))

    print(f"[cmp] {len(pair_rows)} karsilastirma cifti secildi")
    for a, b in pair_rows:
        ka = f"{a.provider_slug}|{a.slug}|{a.variant or ''}"
        kb = f"{b.provider_slug}|{b.slug}|{b.variant or ''}"
        resp = client.get("/karsilastir", params=[("models", ka), ("models", kb),
                                                  ("in", "100000000"), ("out", "25000000")])
        if resp.status_code != 200:
            continue
        slug = f"{a.slug}-vs-{b.slug}".replace("/", "-").lower()[:120]
        target = DIST / "karsilastir" / slug / "index.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        html = resp.text.replace("<head>", '<head>\n<script>window.__STATIC__=true;</script>', 1)
        # SEO: her karsilastirma sayfasi KENDI basligini almali.
        import re as _re2

        # Baslik: okunur ve BENZERSIZ olmali. Once tam slug denenir; 70 karakteri
        # asarsa her iki ad ortadan kisaltilir (bas + son korunur).
        cmp_title = f"{a.slug} vs {b.slug} | TokenMaliyet"
        if len(cmp_title) > 70:
            cmp_title = f"{a.slug} vs {b.slug}"
        if len(cmp_title) > 70:
            cmp_title = f"{_short_slug(a.slug, 30)} vs {_short_slug(b.slug, 30)}"
        if len(cmp_title) > 70:
            cmp_title = f"{_short_slug(a.slug, 22)} vs {_short_slug(b.slug, 22)}"

        cmp_desc = (
            f"{a.name} ve {b.name} aylik maliyet karsilastirmasi: 100M girdi + "
            f"25M cikti token varsayimiyla USD ve TRY fark."
        )[:155]
        html = _re2.sub(r"<title>.*?</title>", f"<title>{cmp_title}</title>", html, count=1, flags=_re2.S)
        html = _re2.sub(r'<meta name="description" content="[^"]*">',
                        f'<meta name="description" content="{cmp_desc}">', html, count=1)
        html = _re2.sub(r'<meta property="og:title" content="[^"]*">',
                        f'<meta property="og:title" content="{cmp_title}">', html, count=1)
        html = _re2.sub(r'<meta property="og:description" content="[^"]*">',
                        f'<meta property="og:description" content="{cmp_desc}">', html, count=1)
        target.write_text(html, encoding="utf-8")

        # --- EN karsilastirma sayfasi (global trafik) ---
        # Turkce'den 10-20 kat fazla aranan Ingilizce sorgular icin ayni cift.
        resp_en = client.get("/en/karsilastir", params=[("models", ka), ("models", kb),
                                                        ("in", "100000000"), ("out", "25000000")])
        if resp_en.status_code == 200:
            target_en = DIST / "en" / "karsilastir" / slug / "index.html"
            target_en.parent.mkdir(parents=True, exist_ok=True)
            html_en = resp_en.text.replace("<head>", '<head>\n<script>window.__STATIC__=true;</script>', 1)
            en_title = f"{a.name} vs {b.name} pricing | TokenMaliyet"
            if len(en_title) > 70:
                en_title = f"{a.slug} vs {b.slug} | TokenMaliyet"
            if len(en_title) > 70:
                en_title = f"{_short_slug(a.slug, 28)} vs {_short_slug(b.slug, 28)}"
            en_desc = (
                f"{a.name} vs {b.name}: monthly API cost for 100M input + 25M output "
                f"tokens. USD list prices with dated TRY equivalent."
            )[:155]
            html_en = _re2.sub(r"<title>.*?</title>", f"<title>{en_title}</title>", html_en, count=1, flags=_re2.S)
            html_en = _re2.sub(r'<meta name="description" content="[^"]*">',
                               f'<meta name="description" content="{en_desc}">', html_en, count=1)
            html_en = _re2.sub(r'<meta property="og:title" content="[^"]*">',
                               f'<meta property="og:title" content="{en_title}">', html_en, count=1)
            html_en = _re2.sub(r'<meta property="og:description" content="[^"]*">',
                               f'<meta property="og:description" content="{en_desc}">', html_en, count=1)
            target_en.write_text(html_en, encoding="utf-8")

    # Cloudflare Pages guvenlik basliklari (rapor 4. tur bolum 6)
    headers_txt = "\n".join([
        "/*",
        "  X-Frame-Options: DENY",
        "  X-Content-Type-Options: nosniff",
        "  Referrer-Policy: strict-origin-when-cross-origin",
        "  Permissions-Policy: camera=(), microphone=(), geolocation=()",
        "  Strict-Transport-Security: max-age=31536000; includeSubDomains; preload",
        "  Content-Security-Policy: default-src 'self'; "
        # Cloudflare Web Analytics beacon (cerezsiz, KVKK dostu) izinli olmali.
        "script-src 'self' 'unsafe-inline' https://static.cloudflareinsights.com https://challenges.cloudflare.com; "
        "style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
        "connect-src 'self' https://cloudflareinsights.com https://challenges.cloudflare.com; "
        "frame-src https://challenges.cloudflare.com; "
        "frame-ancestors 'none'; base-uri 'self'; form-action 'self'",
        "",
        # MIME: yalnizca JSON uclari json; onay/iptal HTML doner (rapor 5. tur Hata 7).
        #
        # DIKKAT (19.11.2026): burada X-Robots-Tag: noindex VARDI. robots.txt ise
        # "Allow: /api/v1/" diyordu. Iki sinyal CELISIYORDU: Google "robots izin
        # veriyor ama sayfa noindex" gorunce taramayi birakiyor; API sayfasi
        # indekslenemiyordu. Site "ucretsiz JSON API" vaat ediyor, o yuzden noindex
        # KALDIRILDI. Form/yazma uclari asagida noindex olarak kaliyor.
        "/api/v1/*",
        "  Content-Type: application/json; charset=utf-8",
        "",
        "/api/uyari",
        "  Content-Type: application/json; charset=utf-8",
        "  X-Robots-Tag: noindex",
        "",
        "/api/iletisim",
        "  Content-Type: application/json; charset=utf-8",
        "  X-Robots-Tag: noindex",
        "",
        # Bulten uclari (10. tur). Fonksiyonlar kendi Content-Type'ini set ediyor
        # ama edge seviyesinde de tutarli olmali; ayrica noindex ile arama
        # motorlarindan uzak tutulur (kayit/cikis akisi indekslenecek icerik degil).
        "/api/bulten",
        "  Content-Type: application/json; charset=utf-8",
        "  X-Robots-Tag: noindex",
        "",
        "/api/bulten-onay",
        "  Content-Type: text/html; charset=utf-8",
        "  X-Robots-Tag: noindex",
        "",
        "/api/bulten-iptal",
        "  Content-Type: text/html; charset=utf-8",
        "  X-Robots-Tag: noindex",
        "",
        "/api/bulten-gonder",
        "  Content-Type: application/json; charset=utf-8",
        "  X-Robots-Tag: noindex",
        "",
        "/api/bildir",
        "  Content-Type: application/json; charset=utf-8",
        "  X-Robots-Tag: noindex",
        "",
        "/api/onayla",
        "  Content-Type: text/html; charset=utf-8",
        "  X-Robots-Tag: noindex",
        "",
        "/api/iptal",
        "  Content-Type: text/html; charset=utf-8",
        "  X-Robots-Tag: noindex",
        "",
    ])
    (DIST / "_headers").write_text(headers_txt, encoding="utf-8")

    # Cloudflare Pages Functions (D1 ile fiyat uyarisi kaydi).
    # dist/functions DEGIL, proje kokundeki /functions Pages tarafindan otomatik bulunur;
    # yine de dist'e kopyalamak zarar vermez ve tek klasor deploy'u kolaylastirir.
    if (ROOT / "functions").exists():
        shutil.copytree(ROOT / "functions", DIST / "functions", dirs_exist_ok=True)

    # --- DIL VE PARA BIRIMI VARYANTLARI ---
    # Statik sitede query string sunucuda islenmiyor. Bu yuzden her kombinasyon
    # AYRI YOL olarak uretiliyor ve dil/para birimi BAGIMSIZ secilebiliyor:
    #   /fiyatlar           /en/fiyatlar           /try/fiyatlar      /en/try/fiyatlar
    #   /gpu-maliyetleri    /en/gpu-maliyetleri    /try/gpu-maliyetleri
    # Kullanici TRY secince dil DEGISMEZ; EN secince para birimi DEGISMEZ.
    VARIANTS = [
        # (temel yol, slug, dil, para birimi)
        ("/fiyatlar", "fiyatlar", "en", "USD"),
        ("/karsilastir", "karsilastir", "en", "USD"),
        ("/hesaplayici", "hesaplayici", "en", "USD"),
        ("/hesaplayici/ses-maliyeti", "hesaplayici/ses-maliyeti", "en", "USD"),
        ("/token-sayaci", "token-sayaci", "en", "USD"),
        ("/gpu-maliyetleri", "gpu-maliyetleri", "en", "USD"),
        ("/uyari", "uyari", "en", "USD"),
        ("/hakkinda", "hakkinda", "en", "USD"),
        ("/fiyatlar", "fiyatlar", "tr", "TRY"),
        ("/gpu-maliyetleri", "gpu-maliyetleri", "tr", "TRY"),
        ("/fiyatlar", "fiyatlar", "en", "TRY"),
        ("/gpu-maliyetleri", "gpu-maliyetleri", "en", "TRY"),
    ]

    def _variant_dir(lang, cur, slug):
        parts = []
        if lang == "en":
            parts.append("en")
        if cur == "TRY":
            parts.append("try")
        return DIST.joinpath(*parts) / slug if parts else DIST / slug

    variant_written = 0
    for path, slug, lang, cur in VARIANTS:
        query = {"lang": lang, "currency": cur}
        resp = client.get(path, params=query)
        if resp.status_code != 200:
            print(f"[skip] {path} {lang}/{cur} -> {resp.status_code}")
            continue
        out_dir = _variant_dir(lang, cur, slug)
        prefix = out_dir.relative_to(DIST).as_posix()
        html = resp.text

        html = html.replace(
            "<head>",
            '<head>\n<script>window.__STATIC__=true;</script>',
            1,
        )
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "index.html").write_text(html, encoding="utf-8")
        variant_written += 1
        print(f"[{lang}/{cur}] /{prefix}")

    print(f"  -> {variant_written} varyant sayfasi uretildi")

    # Anlik arama icin tum modellerin hafif indeksi (rapor 5. tur P1-4).
    # Statik sayfada yalnizca 50 satir var; arama JS'i bu JSON'dan filtreler.
    import json as _json

    from app.db import SessionLocal as _SL3
    from app.web import queries as _q2
    from app.web.render import price_value as _pv

    with _SL3() as _db:
        _rows = [r for r in _q2.price_rows(_db) if r.has_tokens and not r.is_alias]
        index = []
        for r in _rows:
            ip = _pv(r.dim("input"))[0]
            op = _pv(r.dim("output"))[0]
            index.append({
                "n": r.name,
                "p": r.provider_slug,
                "c": r.channel,
                "s": r.slug,
                "i": ip,
                "o": op,
            })
    (DIST / "models-index.json").write_text(
        _json.dumps(index, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )
    print(f"[api] models-index.json -> {len(index)} model")

    # sitemap + robots + static
    (DIST / "sitemap.xml").write_bytes(client.get("/sitemap.xml").content)
    (DIST / "robots.txt").write_bytes(client.get("/robots.txt").content)
    (DIST / "rss.xml").write_bytes(client.get("/rss.xml").content)
    shutil.copytree(ROOT / "backend" / "app" / "web" / "static", DIST / "static", dirs_exist_ok=True)

    # Kok dizin: GERCEK 301 benzeri yonlendirme (meta refresh DEGIL).
    # Meta refresh her bilinmeyen yolu yutuyordu (404 ve /api kiriliyordu).
    # Ana sayfa = HESAPLAYICI. Sitenin amaci token maliyeti hesaplamak;
    # kullanici once isini gormeli. Fiyat listesi menude.
    # Cloudflare Pages: GERCEK 301 (meta refresh degil, rapor 6. tur HATA-7).
    # _redirects yalnizca kok dizine uygulanir; bilinmeyen yollar 404 donmeye devam eder.
    (DIST / "_redirects").write_text(
        "# Cloudflare Pages yonlendirmeleri\n"
        "# Ana sayfa = hesaplayici (sitenin ana isi)\n"
        "/                /hesaplayici/    301\n"
        "# Eski /docs baglantilari (FastAPI varsayilani) artik gercek API sayfasina gider.\n"
        "# Statik sitede Python sunucu yok; bu yuzden yonlendirme Pages katmaninda yapilir.\n"
        "/docs            /api-dokumantasyon/    301\n"
        "/docs/*          /api-dokumantasyon/    301\n",
        encoding="utf-8",
    )
    # _redirects desteklemeyen ortamlar icin (yerel onizleme) kucuk yedek sayfa.
    (DIST / "index.html").write_text(
        '<!DOCTYPE html><html lang="tr"><head><meta charset="utf-8">'
        '<title>TokenMaliyet - AI API maliyet hesaplayici</title>'
        '<meta name="description" content="AI API ve GPU maliyetlerini hesaplayin: '
        '480+ model, 5 saglayici, tarihli TRY kuru. Ucretsiz hesaplayici.">'
        '<meta name="robots" content="noindex,follow">'
        '<link rel="canonical" href="https://tokenmaliyet.com/hesaplayici/">'
        '<meta http-equiv="refresh" content="0; url=/hesaplayici/">'
        '</head><body><h1>TokenMaliyet</h1>'
        '<p><a href="/hesaplayici/">Maliyet hesaplayiciya git</a></p></body></html>',
        encoding="utf-8",
    )

    # 404: bilinmeyen yollar /fiyatlar'a YONLENDIRILMEZ, gercek 404 doner.
    notfound = """<!DOCTYPE html><html lang="tr"><head><meta charset="utf-8">
    <meta name="robots" content="noindex">
    <title>Sayfa bulunamadi (404) - TokenMaliyet</title>
    <link rel="stylesheet" href="/static/app.css"></head>
    <body><main class="container" style="padding:64px 0;max-width:640px">
    <h1>Sayfa bulunamadi</h1>
    <p class="lede">Aradiginiz sayfa tasinmis veya hic var olmamis olabilir.</p>
    <p><a class="btn" href="/fiyatlar/">AI API fiyatlarina git</a></p>
    <h2 style="font-size:var(--fs-h3);margin-top:32px">Populer sayfalar</h2>
    <ul><li><a href="/fiyatlar/">AI API fiyatlari</a></li>
    <li><a href="/gpu-maliyetleri/">GPU kiralama maliyetleri</a></li>
    <li><a href="/hesaplayici/">Maliyet hesaplayici</a></li>
    <li><a href="/turkce-token-maliyeti/">Turkce token farki</a></li>
    <li><a href="/rehber/">Rehber</a></li></ul>
    </main></body></html>"""
    (DIST / "404.html").write_text(notfound, encoding="utf-8")

    # API: /api/v1/model-options GERCEK JSON olarak uretilir.
    # Onceki hata (rapor 5. tur Hata 2): buraya sabit hata mesaji yaziliyordu;
    # token sayaci list.forEach() cagirinca TypeError aliyor ve fiyatlar
    # sonsuza kadar "yukleniyor" kaliyordu.
    # API uclari STATIK olarak da uretilmeli.
    # Gercek hata (15.11.2026 canli test): alt bilgi ve hakkinda sayfasi
    # /api/v1/prices?format=json adresine baglanti veriyordu ama Cloudflare Pages'te
    # Python sunucu olmadigi icin bu adres 404 donuyordu. "Ucretsiz JSON" sozu tutmuyordu.
    api_dir = DIST / "api" / "v1"
    api_dir.mkdir(parents=True, exist_ok=True)
    API_ENDPOINTS = [
        ("model-options", "/api/v1/model-options"),
        ("prices", "/api/v1/prices"),
        ("fx", "/api/v1/fx?quote=TRY"),
        ("providers", "/api/v1/providers"),
    ]
    for name, url in API_ENDPOINTS:
        resp_api = client.get(url)
        if resp_api.status_code == 200:
            (api_dir / name).write_bytes(resp_api.content)
            print(f"[api] {name} -> {len(resp_api.content)} bayt JSON")
        else:
            (api_dir / name).write_text("[]", encoding="utf-8")
            print(f"[api] {name} URETILEMEDI ({resp_api.status_code}), bos liste yazildi")

    # --- Ic baglanti normalizasyonu ---
    # Cloudflare Pages sayfalari /fiyatlar/ biciminde sunuyor ve /fiyatlar istegini
    # 308 ile yonlendiriyor. Kanonik adresler artik / ile bitiyor; ic baglantilar da
    # ayni bicimde olmali ki her gezinme gereksiz bir yonlendirme harcamasin.
    _finalize_pages()
    _fix_jsonld_urls()

    print(f"\nSTATIK EXPORT TAMAM: {written} sayfa -> {DIST}")
    return 0


def _short_slug(slug: str, limit: int = 30) -> str:
    """Slug'i ORTADAN kisaltir: bas ve son korunur.

    Model adlarinda ayirt edici bilgi iki ucta olur:
      gemini-3.1-flash-lite-image   -> model ailesi basta, tur sonda
      gemini-2.5-flash-preview-tts  -> "flash"/"pro" basta, "tts" sonda
    Ortadan kisaltma ikisini de korur; sadece sonda kirpmak "flash"/"pro"
    ayrimini yok ediyordu (onceki hata).
    """
    if len(slug) <= limit:
        return slug
    head_len = max(8, limit // 2)
    tail_len = max(6, limit - head_len - 1)      # 1 = "…"
    return f"{slug[:head_len]}…{slug[-tail_len:]}"


def _dedupe_titles() -> None:
    """Ayni <title> metnini tasiyan sayfalari GARANTILI bicimde ayirir.

    Neden son gecis: baslik metnini onceden kisaltmak kirilgan; model adlari
    uzadikca iki farkli cift ayni kisaltmaya dusuyor. Burada once tum basliklar
    toplanir, GERCEK cakismalar bulunur ve her sayfaya, gruptaki diger
    sayfalardan AYRISTIGI parcadan turetilen bir ek konur. Son care olarak
    yolun kisa ozeti eklenir; boylece benzersizlik garanti edilir.
    """
    import hashlib
    import re as _re

    title_re = _re.compile(r"<title>(.*?)</title>", _re.S)

    for _round in range(3):
        current: dict[Path, str] = {}
        for p in sorted(DIST.rglob("*.html")):
            m = title_re.search(p.read_text(encoding="utf-8"))
            if m:
                current[p] = m.group(1).strip()

        by_title: dict[str, list[Path]] = {}
        for p, t in current.items():
            by_title.setdefault(t, []).append(p)

        groups = {t: ps for t, ps in by_title.items() if len(ps) > 1}
        if not groups:
            if _round:
                print(f"[title] mukerrer baslik kalmadi ({_round} gecis)")
            return

        fixed = 0
        for title, paths in groups.items():
            # Gurubu yollarin token kumeleriyle ayirt et.
            tokens = {p: set(p.parent.relative_to(DIST).as_posix().replace("/", "-").split("-"))
                      for p in paths}
            for p in paths:
                others = [tokens[q] for q in paths if q is not p]
                unique_bits = tokens[p] - set().union(*others) if others else set()
                # Anlamli (sayisal olmayan, kisa olmayan) parcalari tercih et.
                marker = ""
                if unique_bits:
                    good = [w for w in unique_bits if len(w) > 2 and not w.isdigit()]
                    pick = good or sorted(unique_bits)
                    marker = "-".join(sorted(pick, key=len, reverse=True)[:2])[:20]
                if not marker:
                    rel = p.parent.relative_to(DIST).as_posix()
                    marker = hashlib.sha1(rel.encode()).hexdigest()[:6]
                if f"({marker})" in title:
                    marker = hashlib.sha1(
                        p.parent.relative_to(DIST).as_posix().encode()).hexdigest()[:6]
                new_title = f"{title[:50].rstrip(' ·—-')} ({marker})"
                src = p.read_text(encoding="utf-8")
                p.write_text(title_re.sub(lambda _m: f"<title>{new_title}</title>", src, count=1),
                             encoding="utf-8")
                fixed += 1
        print(f"[title] {fixed} mukerrer baslik ayirt edildi (gecis {_round + 1})")


def _normalize_site_urls(value):
    """JSON-LD icindeki site URL'lerini dizin bicimine cevirir (recursive)."""
    base = "https://tokenmaliyet.com"
    if isinstance(value, str):
        if value.startswith(base):
            rest = value[len(base):]
            # Sorgu dizesi varsa korunur (/fiyatlar?provider=x)
            path, sep, query = rest.partition("?")
            last = path.rsplit("/", 1)[-1]
            # Uzantili dosyalar (sitemap.xml, og-image.png) dokunulmaz
            if path and not path.endswith("/") and "." not in last:
                path += "/"
            return base + path + (sep + query if sep else "")
        return value
    if isinstance(value, list):
        return [_normalize_site_urls(v) for v in value]
    if isinstance(value, dict):
        return {k: _normalize_site_urls(v) for k, v in value.items()}
    return value


def _fix_jsonld_urls() -> None:
    """Tum JSON-LD bloklarini yeniden yazar: gecerli JSON + dizin bicimi URL."""
    import json
    import re as _re

    pat = _re.compile(
        r'<script type="application/ld\+json">([\s\S]*?)</script>', _re.S
    )
    fixed = 0
    invalid = 0
    for html_file in DIST.rglob("*.html"):
        src = html_file.read_text(encoding="utf-8")

        def repl(m):
            nonlocal fixed, invalid
            raw = m.group(1)
            try:
                data = json.loads(raw)
            except Exception:
                invalid += 1
                # Bozuk JSON'u sessizce gecmeyelim: konsola yaz ki fark edilsin.
                print(f"[jsonld] GECERSIZ JSON: {html_file.relative_to(DIST)}")
                return m.group(0)
            before = raw
            data = _normalize_site_urls(data)
            out = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
            if out != before.strip():
                fixed += 1
            return '<script type="application/ld+json">' + out + "</script>"

        new = pat.sub(repl, src)
        if new != src:
            html_file.write_text(new, encoding="utf-8")
    print(f"[jsonld] {fixed} blok guncellendi, {invalid} gecersiz")


def _finalize_pages() -> None:
    """Her uretilen sayfaya KENDI kanonik adresini yazar ve ic baglantilari duzeltir.

    Neden tek gecis: daha once kanonik adresler sayfa basina ayri ayri string
    degistirmeyle yaziliyordu; bicim degisince ( / ile biten adres ) bu degistirmeler
    sessizce eslesmiyor ve sayfalar YANLIS kanonik gosteriyordu. Artik kaynak tek:
    sayfanin kendi cikti yolu.
    """
    import re as _re

    base = "https://tokenmaliyet.com"
    href_re = _re.compile(r'href="(/[^"#?]*)"')
    can_re = _re.compile(r'<link rel="canonical" href="[^"]*">')
    og_re = _re.compile(r'<meta property="og:url" content="[^"]*">')
    og_desc_re = _re.compile(r'<meta property="og:description" content="[^"]*">')

    def fix_href(match):
        path = match.group(1)
        if path == "/" or path.endswith("/"):
            return match.group(0)
        if path.startswith(("/static/", "/api/", "/functions/")):
            return match.group(0)
        last = path.rsplit("/", 1)[-1]
        if "." in last:
            return match.group(0)
        return f'href="{path}/"'

    title_re = _re.compile(r"<title>(.*?)</title>", _re.S)
    MAX_TITLE = 60
    SUFFIX = " | TokenMaliyet"

    links_changed = 0
    canon_changed = 0
    title_changed = 0
    for html_file in DIST.rglob("*.html"):
        rel = html_file.parent.relative_to(DIST).as_posix()
        # KOK index.html yonlendirme sayfasidir; kanonigi hesaplayiciya isaret eder.
        if rel == ".":
            own = f"{base}/hesaplayici/"
        else:
            own = f"{base}/{rel}/"

        src = html_file.read_text(encoding="utf-8")
        new = href_re.sub(fix_href, src)

        # --- Model sayfasi basligi BENZERSIZ olmali ---
        # Kisa adli iki model (orn. ...-image / ...-preview) 30 karakterde
        # kisaltilinca ayni basligi uretiyordu -> mukerrer baslik.
        # Cozum: uzun adlarda basligin sonuna KISA SLUG eki eklenir.
        if rel.startswith("modeller/"):
            m_model = title_re.search(new)
            if m_model:
                t0 = m_model.group(1).strip()
                stem0 = t0[: -len(SUFFIX)] if t0.endswith(SUFFIX) else t0
                slug_tail = rel.rsplit("/", 1)[-1]
                # Kisaltilmis basliklarda ayirt edici son eki ekle.
                # 'gemini-3.1-flash-lite-image' ile '...-preview' ayni basliga
                # kisaliyordu; ayirt eden parca slug'in SON parcasidir.
                if "…" in stem0:
                    last_tok = slug_tail.rsplit("-", 1)[-1]
                    if last_tok and last_tok not in stem0:
                        room = MAX_TITLE - len(SUFFIX) - len(last_tok) - 4
                        t1 = f"{stem0[:room].rstrip(' ·—-')} · {last_tok}{SUFFIX}"
                        new = title_re.sub(f"<title>{t1}</title>", new, count=1)
                        title_changed += 1

        # --- Baslik kurallari (SEO) ---
        # 1) 60 karakteri asan baslik Google'da kesilir; model adi kismini kisalt.
        # 2) /try/ varyantlari ayni basligi tasiyordu -> mukerrer baslik. Para birimi eklenir.
        m_title = title_re.search(new)
        if m_title and not rel.startswith("karsilastir"):
            title = m_title.group(1).strip()
            original = title

            def _shorten(t: str, budget: int) -> str:
                """Basligi, anlamli parcalari koruyarak 'budget' karaktere sigdirir."""
                if len(t) <= budget:
                    return t
                stem = t[: -len(SUFFIX)] if t.endswith(SUFFIX) else t
                # 1) " — <aciklama>" kismini at (ana konu korunur)
                for sep in (" — ", " – ", " · "):
                    if sep in stem:
                        head = stem.split(sep, 1)[0]
                        if len(head) + len(SUFFIX) <= budget:
                            return head + SUFFIX
                # 2) Kelime sinirinda kirp
                keep = budget - len(SUFFIX) - 1
                cut = (t[: -len(SUFFIX)] if t.endswith(SUFFIX) else t)[:keep]
                if " " in cut:
                    cut = cut.rsplit(" ", 1)[0]
                return cut.rstrip(" ·—-") + "…" + SUFFIX

            is_try = rel.startswith("try/") or rel.startswith("en/try/")
            # DIKKAT: sira onemli. Once baslik kisaltilir, SONRA para birimi eki eklenir.
            # Onceki hata: ek once eklenip sonra kisaltiliyordu; kisaltma " — " ayiricindan
            # boldugu icin ek de siliniyor ve TRY varyanti USD ile AYNI basligi aliyordu.
            title = _shorten(title, MAX_TITLE)
            if is_try and "TRY" not in title:
                marker = " — TRY"
                if len(title) + len(marker) <= MAX_TITLE:
                    title = title.replace(SUFFIX, "") + marker + SUFFIX
                else:
                    title = _shorten(title, MAX_TITLE - len(marker)).replace(SUFFIX, "") + marker + SUFFIX

            if title != original:
                new = title_re.sub(f"<title>{title}</title>", new, count=1)
                title_changed += 1

        if can_re.search(new):
            replaced = can_re.sub(f'<link rel="canonical" href="{own}">', new, count=1)
            if replaced != new:
                canon_changed += 1
            new = replaced
        if og_re.search(new):
            new = og_re.sub(f'<meta property="og:url" content="{own}">', new, count=1)

        # Description 160 karakteri asarsa kesilir (Google tam gostermiyor).
        d_re = _re.compile(r'<meta name="description" content="([^"]*)">')
        m_desc = d_re.search(new)
        if m_desc and len(m_desc.group(1)) > 160:
            cut = m_desc.group(1)[:157].rstrip(" ,.;:—-")
            new = d_re.sub(f'<meta name="description" content="{cut}…">', new, count=1)
            new = og_desc_re.sub(f'<meta property="og:description" content="{cut}…">', new, count=1)

        if new != src:
            html_file.write_text(new, encoding="utf-8")
            links_changed += 1
    print(f"[link] {links_changed} sayfada baglanti/kanonik guncellendi")
    print(f"[canonical] {canon_changed} sayfaya kendi kanonik adresi yazildi")
    print(f"[title] {title_changed} baslik uzunluk/benzersizlik icin guncellendi")
    _dedupe_titles()


def _normalize_internal_links() -> None:
    """Ic href'leri dizin bicimine cevirir; dosya/API/dis baglantilarina dokunmaz."""
    import re as _re

    href_re = _re.compile(r'href="(/[^"#?]*)"')

    def fix(match):
        path = match.group(1)
        # Dokunulmayacaklar: dis adres, varlik, API, uzantili dosya, kok
        if path == "/" or path.endswith("/"):
            return match.group(0)
        if path.startswith(("/static/", "/api/", "/functions/")):
            return match.group(0)
        last = path.rsplit("/", 1)[-1]
        if "." in last:          # sitemap.xml, robots.txt, og-image.png ...
            return match.group(0)
        return f'href="{path}/"'

    changed = 0
    for html_file in DIST.rglob("*.html"):
        src = html_file.read_text(encoding="utf-8")
        new = href_re.sub(fix, src)
        if new != src:
            html_file.write_text(new, encoding="utf-8")
            changed += 1
    print(f"[link] {changed} HTML dosyasinda ic baglanti / ile bitirildi")


if __name__ == "__main__":
    raise SystemExit(main())
