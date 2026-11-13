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
    ("/token-sayaci", "token-sayaci"),
    ("/turkce-token-maliyeti", "turkce-token-maliyeti"),
    ("/gpu-maliyetleri", "gpu-maliyetleri"),
    ("/degisiklikler", "degisiklikler"),
    ("/rehber", "rehber"),
    ("/hakkinda", "hakkinda"),
    ("/danismanlik", "danismanlik"),
    ("/gizlilik", "gizlilik"),
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

    with SessionLocal() as db:
        count = 0
        for row in queries.price_rows(db):
            if not dm.is_indexable(row):
                continue
            resp = client.get(f"/modeller/{row.provider_slug}/{row.slug}")
            if resp.status_code != 200:
                continue
            target = DIST / "modeller" / row.provider_slug / row.slug / "index.html"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(resp.text, encoding="utf-8")
            count += 1
            if count >= 60:
                break

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
        # canonical: bu sayfanin kendisi
        html = html.replace(
            '<link rel="canonical" href="https://tokenmaliyet.com/gpu-maliyetleri">',
            f'<link rel="canonical" href="https://tokenmaliyet.com/gpu/{slug}">',
            1,
        )
        # robots: indekslenebilir
        html = html.replace(
            '<meta name="robots" content="noindex,nofollow">',
            '<meta name="robots" content="index,follow,max-image-preview:large">',
            1,
        )
        target = DIST / "gpu" / slug / "index.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(html, encoding="utf-8")
        print(f"[ok] /gpu/{slug}")

    # Programatik karsilastirma sayfalari (rapor 4. tur: populer 20 cift)
    from app.db import SessionLocal as _SL2
    from app.web import default_models as _dm
    from app.web import queries as _q

    populer = []
    with _SL2() as db2:
        for row in _q.price_rows(db2):
            if _dm.is_indexable(row):
                populer.append(row)
            if len(populer) >= 8:
                break

    import itertools
    for a, b in itertools.islice(itertools.combinations(populer, 2), 20):
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
        # Her karsilastirma sayfasi KENDI canonical'ini almali (yoksa mukerrer sayilir).
        html = html.replace(
            '<link rel="canonical" href="https://tokenmaliyet.com/karsilastir">',
            f'<link rel="canonical" href="https://tokenmaliyet.com/karsilastir/{slug}">',
            1,
        )
        target.write_text(html, encoding="utf-8")

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
        "/api/v1/*",
        "  Content-Type: application/json; charset=utf-8",
        "  X-Robots-Tag: noindex",
        "",
        "/api/uyari",
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

        # canonical: bu varyantin kendi adresi
        html = html.replace(
            f'<link rel="canonical" href="https://tokenmaliyet.com{path}">',
            f'<link rel="canonical" href="https://tokenmaliyet.com/{prefix}">',
            1,
        )
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
        "/                /hesaplayici/    301\n",
        encoding="utf-8",
    )
    # _redirects desteklemeyen ortamlar icin (yerel onizleme) kucuk yedek sayfa.
    (DIST / "index.html").write_text(
        '<!DOCTYPE html><html lang="tr"><head><meta charset="utf-8">'
        '<title>TokenMaliyet - AI API maliyet hesaplayici</title>'
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
    api_dir = DIST / "api" / "v1"
    api_dir.mkdir(parents=True, exist_ok=True)
    resp_options = client.get("/api/v1/model-options")
    if resp_options.status_code == 200:
        (api_dir / "model-options").write_bytes(resp_options.content)
        print(f"[api] model-options -> {len(resp_options.content)} bayt JSON")
    else:
        (api_dir / "model-options").write_text("[]", encoding="utf-8")
        print(f"[api] model-options URETILEMEDI ({resp_options.status_code}), bos liste yazildi")

    print(f"\nSTATIK EXPORT TAMAM: {written} sayfa -> {DIST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
