# 4. Tur Denetim Raporu - Uygulama Durumu

Kaynak: `TokenMaliyetKapsamliGelistirmeveDenetimRaporu.pdf` (12.11.2026)
Uygulama: 12.11.2026 - **136 test geciyor** - commitler: 8c8e938, 8e70370, 7953ecb

---

## 5 kritik bulgu - hepsi once OLCULDU, sonra duzeltildi

### P0-1 - GPU sutun kaymasi - DUZELTILDI

**Rapor:** GB300 satirinda EN DUSUK FIYAT altinda 0,0481 $, $/GB VRAM altinda 13,86 USD.

**Dogrulama:** Evet, gercekti. Hucre sirasi `GPU|VRAM|$/GB|En dusuk` iken baslik sirasi
`GPU|VRAM|En dusuk|$/GB` idi.

| Konum | Baslik | Hucre (oncesi) | Hucre (sonrasi) |
|---|---|---|---|
| 3 | En dusuk fiyat | ~~0,0481 $~~ | **13,86 USD** |
| 4 | $/GB VRAM | ~~13,86 USD~~ | **0,0481 $** |

**Kalici koruma:** `test_gpu_columns_match_cells` + `test_gpu_hourly_greater_than_per_gb_strict`

### P0-2 - Compare 3-4 kutular dolu - DUZELTILDI

**Kok neden:** Sunucu tarafi dogruydu ama `base.html` icindeki JS secenekleri yeniden
yazarken `<option value="">- secin -</option>` placeholder'ini siliyordu; tarayici ilk modeli
otomatik seciyordu. Yani **sunucu dogru, istemci yanlis**.

**Duzeltme:** `apply()` placeholder'i koruyor; secim yalnizca acik istek varsa yapiliyor.
**Dogrulama:** m0 ve m1 dolu, **m2 ve m3 bos**.

### P0-3 - Sessiz Turkce carpani - DUZELTILDI

Compare formuna **METIN DILI** secicisi (Turkce 2,29x / Ingilizce 1,00x) + sonuc basliginda
**"Turkce icerik varsayimi - 2,29x (tahmin)"** rozeti eklendi.

### P1-4 - Hesaplayici bilgi kutusu - DUZELTILDI

"**her iki modelin** maliyeti de ayni Turkce token carpaniyla hesaplandi... Bu bir tahmindir"
+ ondalik virgul (2,29x).

### P1-5 - Sabit metin celiskileri - DUZELTILDI

| Celiski | Duzeltme |
|---|---|
| "uc kisa yazi" ama 4 kart | `{{ guides\|length }} kisa yazi` -> **4** |
| "4 saglayici" vs Hakkinda 5 | Lede: "430 model: **3 resmi saglayici API'si ve 1 pazaryeri**" |
| Changes H1 "Bu hafta" ama 30 gun | H1: "**Fiyatlarda ne degisti?**" |
| "resmi sayfalardan" ama pazaryeri var | "...**ve OpenRouter pazaryeri API'sinden**" |

---

## Raporun diger bolumleri

### 2.1 - Binlik ayirici + hizli token cipleri - YAPILDI

Input alanlari `100.000.000` biciminde; altinda **1M / 10M / 50M / 100M / 500M / 1B** cipleri.
Form altinda ozet: "100M girdi + 25M cikti token".

### 2.1 - Kisa siralama etiketleri - YAPILDI

"Onerilen (bilinen s..." -> **"Onerilen"**, "VRAM (buyuk -> k..." -> **"VRAM: yuksek -> dusuk"**.

### 2.1 - Para birimi senkronizasyonu - KISMI

Ana birim USD'de tutuldu (kaynak fiyati USD); TL ikincil satirda. Ust menudeki TRY secimi
tabloyu ceviriyor ama **hesaplayici sonuc kartlarini degistirmiyor** - bu acik kaldi.

### 2.2 - Satir ici aksiyonlar - YAPILMADI

Hesap makinesi ikonu, yuzen karsilastirma sepeti, model ID kopyalama - ucu de eklenmedi.
Gerekce: her biri ayri JS bileseni; statik hosting gecisiyle birlikte ele alinmali.

### 2.3 - Statik hosting icin istemci tarafli URL - YAPILDI

`base.html`'e `initFromQuery()` eklendi: `from/to/models/in/out/dil/cache/currency/lang/q/
provider/kind/sort` parametrelerini okur. Statik sayfalarda `window.__STATIC__=true` bayragi ile
GET formlari JS'e devredilir; export sirasinda enjekte ediliyor.

### 3.1 - Yeni ozellikler - KISMI

| Ozellik | Durum |
|---|---|
| Baglam penceresi + yetenek rozetleri | HAYIR - veri DB'de yok |
| API vs GPU interaktif hesaplayici | KISMI - rehber var, interaktif degil |
| E-posta uyarilari | VAR (`/uyari`); satir ici entegrasyon yok |
| RSS / JSON feed | HAYIR |
| Embed badge | HAYIR |
| 300 cumlelik olcum | HAYIR - hala 20 cumle |

### 3.2 - Cikarilacaklar - YAPILDI

- Mukerrer "Model ara" butonu `/fiyatlar`'da kaldirildi
- Compare'deki cift gorsellestirme: kart ici cubuk kaldirildi, etiketli grafik kaldi
- Changes'deki ham parser loglari **kapali akordeona** tasindi
- `DEPLOY_UCRETSIZ.md`'deki `.ps1` referansi `python scripts/export_static.py` oldu

### 4 - SEO - BUYUK OLCUDE YAPILDI

| Madde | Durum |
|---|---|
| Programatik model/GPU sayfalari | **39 GPU + 20 karsilastirma** sayfasi uretildi |
| Dataset + BreadcrumbList + Article JSON-LD | VAR (3. turda eklendi, dogrulandi) |
| Canonical + noindex kurallari | VAR |
| Sitemap `lastmod` | YOK (changefreq var) |
| hreflang | HAYIR - Ingilizce icerik yok |
| og:image uretimi | HAYIR |

### 5 - Gelir - YAPILMADI (bilincli)

Affiliate, sponsorluk, Pro katman - hicbiri eklenmedi. Gerekce: program basvurulari ve
mali musavir gorusu sizde; kod tarafi hazir olmadan link koymak guveni zedeler.

### 6 - Guvenlik - BUYUK OLCUDE YAPILDI

| Madde | Durum |
|---|---|
| Cloudflare `_headers` (CSP/HSTS/frame-ancestors) | export'a eklendi |
| Statik cikti izolasyon testi | **sizinti yok** (ADMIN_TOKEN, DATABASE_URL, admin, stack trace) |
| Admin token sabit zamanli karsilastirma | `hmac.compare_digest` |
| Varsayilan/zayif anahtar reddi | 32 karakter alti uretimde panel kapali |
| `security.txt` | VAR |
| Sifreli yedek + saglik kontrolu | `scripts/health_and_backup.ps1` (gpg AES256) |
| Scraper SSRF/XSS | Jinja2 otomatik kacis; `\|safe` kullanimi yok |
| Rate limit / Turnstile / Cloudflare Access | HAYIR - altyapi tarafi, kod disi |

---

## Dogrulama

```
136 passed, 5 skipped in 9.93s
14/14 kabul kriteri PASS
Statik export: 97 sayfa, 2,4 MB
Statik izolasyon: temiz (sizinti yok)
_headers: CSP + HSTS + frame-ancestors var
sitemap: 56 URL
```

**Kabul kriteri tablosu (14/14):** GPU sutun sirasi - saatlik > $/GB - Compare 3-4 bos -
Compare dil secici - carpan rozeti - "her iki modelin" - virgullu ondalik - rehber dinamik sayi -
Changes H1 - pazaryeri aciklamasi - binlik ayirici - token cipleri - kisa siralama etiketi -
mukerrer buton kaldirildi

---

## Bir hata yaptim ve duzelttim

4. tur commit'inde (`8c8e938`) `docs/` altindaki 6 rapor dokumani yanlislikla silindi.
Fark ettim, git'ten geri yukledim, ayri commit attim (`ff0b555`). Su an 9 dokuman yerinde.

---

## Acik kalanlar (durust liste)

1. **Para birimi senkronizasyonu** (2.1) - hesaplayici kartlari TRY secimini yansitmiyor
2. **Satir ici aksiyonlar** (2.2) - hesap ikonu, sepet, ID kopyalama yok
3. **Yetenek rozetleri** (3.1) - baglam penceresi/modalite verisi DB'de yok
4. **RSS/JSON feed, embed badge** - yok
5. **300 cumlelik olcum** - hala 20 cumle
6. **Gelir katmanlari** - bilincli olarak yok
7. **hreflang, og:image, sitemap lastmod** - yok
8. **Rate limit / Turnstile / Cloudflare Access** - altyapi kurulumu gerekiyor

## Sizden gerekenler

1. **ADMIN_TOKEN** - 32+ karakter (artik zorunlu)
2. **SITE_URL** + alan adi
3. **Cloudflare Pages** projesi -> `dist/` yukle
4. **Search Console** -> `/sitemap.xml`
5. Affiliate basvurulari, mali musavir gorusu
