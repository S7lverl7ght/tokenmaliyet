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

    # Cloudflare Pages guvenlik basliklari (rapor 4. tur bolum 6)
    (DIST / "_headers").write_text(
        "/*\n"
        "  X-Frame-Options: DENY\n"
        "  X-Content-Type-Options: nosniff\n"
        "  Referrer-Policy: strict-origin-when-cross-origin\n"
        "  Permissions-Policy: camera=(), microphone=(), geolocation=()\n"
        "  Strict-Transport-Security: max-age=31536000; includeSubDomains; preload\n"
        "  Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; "
        "frame-ancestors 'none'; base-uri 'self'; form-action 'self'\n",
        encoding="utf-8",
    )

    # sitemap + robots + static
    (DIST / "sitemap.xml").write_bytes(client.get("/sitemap.xml").content)
    (DIST / "robots.txt").write_bytes(client.get("/robots.txt").content)
    shutil.copytree(ROOT / "backend" / "app" / "web" / "static", DIST / "static", dirs_exist_ok=True)

    # Kok dizin /fiyatlar'a yonlensin (statik ortamda redirect)
    (DIST / "index.html").write_text(
        '<!DOCTYPE html><meta charset="utf-8">'
        '<meta http-equiv="refresh" content="0; url=/fiyatlar/">'
        '<link rel="canonical" href="/fiyatlar/">'
        '<title>TokenMaliyet</title>'
        '<p><a href="/fiyatlar/">Fiyatlara git</a></p>',
        encoding="utf-8",
    )

    print(f"\nSTATIK EXPORT TAMAM: {written} sayfa -> {DIST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
