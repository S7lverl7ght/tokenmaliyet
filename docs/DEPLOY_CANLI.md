# Deploy Kaydi - tokenmaliyet.com

Tarih: 12.11.2026

## Canli durum

| Bilesen | Deger |
|---|---|
| Alan adi | **tokenmaliyet.com** + www (Cloudflare Registrar) |
| Hosting | **Cloudflare Pages** (proje: tokenmaliyet) |
| DNS | 2 CNAME -> tokenmaliyet.pages.dev (proxied) |
| SSL | Google sertifikasi, otomatik (Cloudflare) |
| Account ID | 279485e31b16d58ec7d5603dead31b90 |
| Zone ID | 98091f09564a94a1c95b11134774e7e8 |
| Sayfa sayisi | **105 dosya** (17 ana + 39 GPU + 20 karsilastirma + model sayfalari) |
| Boyut | ~2,5 MB |

## Dogrulanan

```
15/15 sayfa HTTP 200
Guvenlik basliklari: HSTS, CSP, X-Frame-Options, X-Content-Type-Options,
                     Referrer-Policy, Permissions-Policy -> hepsi VAR
canonical: https://tokenmaliyet.com/fiyatlar
Fiyat ve model verisi HTML icinde (JS'siz okunabilir)
sitemap.xml: 56 URL, hepsi https
robots.txt: Sitemap satiri dogru
```

## Yapilan islemler

1. bsk CLI ile Chrome'a baglandi (daemon foreground job olarak)
2. wrangler login OAuth akisi: Chrome'da yetkilendirme onaylandi
3. wrangler pages project create tokenmaliyet -> proje olustu
4. python scripts/export_static.py -> dist/ (SITE_URL=https://tokenmaliyet.com)
5. wrangler pages deploy dist -> 104 dosya yuklendi
6. Cloudflare API (OAuth token) ile custom domain eklendi: apex + www
7. Panel uzerinden 2 CNAME DNS kaydi eklendi
8. Domain durumu: active / validation: active (her ikisi)

## Guvenlik

- .env icine **64 karakterlik** rastgele ADMIN_TOKEN uretildi
- .env git'te takip edilmiyor (.gitignore)
- Statik ciktida sir/admin/stack trace yok (test ile dogrulandi)

## Yeniden deploy

```powershell
cd C:\AI-Maliyet-Merkezi
$env:PYTHONPATH="$PWD\backend"; $env:SITE_URL="https://tokenmaliyet.com"
.\.venv\Scripts\python.exe .\scripts\export_static.py
npx wrangler pages deploy dist --project-name=tokenmaliyet --branch=main
```

## Bilinen sinirlar

- **Apex -> www yonlendirmesi yok**: her iki host da ayni icerigi sunuyor,
  canonical https://tokenmaliyet.com (www'suz). Google icin sorun degil
  (canonical tek). Istenirse Cloudflare Redirect Rules ile 301 eklenebilir.
- **Yerel DNS** pages.dev alan adini yanlis cozuyor (Turk Telekom DNS
  yonlendirmesi). Bu makineden *.pages.dev testleri basarisiz gorunebilir;
  ozel alan adi (tokenmaliyet.com) sorunsuz calisiyor.
- **Veri yenileme henuz otomatik degil**: GitHub Actions workflow'u hazir
  (.github/workflows/refresh.yml) ama repo GitHub'a push edilmedi.
  Push edilince gunluk 06:10 ve 18:10'da calisacak.
