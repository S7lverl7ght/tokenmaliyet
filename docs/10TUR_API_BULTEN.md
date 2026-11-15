# 10. Tur — Canonical, API, /docs ve Bülten (15.11.2026)

Kullanıcının üç maddesi uygulandı. Birinde **önerilen düzeltme yanlıştı** ve gerekçesiyle birlikte
aşağıda açıklandı.

---

## Madde 1 — Canonical / og:url

**Öneri:** `<link rel="canonical" href="{{ page.url }}">` — "/hesaplayici/ için /hesaplayici,
"/en/hesaplayici/ için /en/hesaplayici".

**Canlı test sonucu:** `/hesaplayici` isteği **308 ile `/hesaplayici/` adresine yönleniyor**.

```
HTTP/1.1 308 Permanent Redirect
Location: /hesaplayici/
```

Bu yüzden öneriyi harfiyen uygulamak, kullanıcının kaçınmak istediği hatayı **yaratırdı**:
canonical etiketi 308 dönen bir adresi gösterir, Google "kanonik adres yönlendiriyor" der ve
sinyal kaybolur. Şu an doğru olan biçim kullanılıyor: sayfanın **kendi 200 dönen adresi**.

| Kontrol | Sonuç |
|---|---|
| 490 sayfada canonical == sayfanın kendi adresi | **0 uyuşmazlık** |
| 490 sayfada og:url == canonical | **0 uyuşmazlık** |
| Eğik çizgi yok sayıldığında uyuşmazlık | **0** |

Zaten her sayfa kendini kanonik gösteriyor: `/hesaplayici/` → `/hesaplayici/`,
`/en/hesaplayici/` → `/en/hesaplayici/`, `/en/try/fiyatlar/` → `/en/try/fiyatlar/`.

**Doğrulama testi:** `test_canonical_and_og_are_same_url`

---

## Madde 2 — API + /docs gerçekten çalışsın, robots'tan Disallow: /api/ kalksın

### robots.txt

```diff
- Disallow: /api/
+ Allow: /
+ Allow: /api/v1/
+ Disallow: /api/uyari      (form POST, indekslenecek içerik yok)
+ Disallow: /api/iletisim
+ Disallow: /api/bulten
+ Disallow: /api/bulten-onay
+ Disallow: /api/bulten-iptal
```

Gerekçe: site "ücretsiz JSON API" vaat ediyor ve API sayfası buna bağlantı veriyordu;
robots ile engellemek bu vaatle çelişiyordu. Fiyat verisi kamuya açık ve ticari değer taşıyor.
Yalnızca gerçekten gizli (admin) ve yazma işlemi yapan form uçları kapalı kaldı.

### /docs

Önceden 404 dönüyordu (statik sitede Python sunucusu yok, FastAPI'nin `/docs`'u yok).
Artık **gerçek içerikli bir sayfa** var:

- `/api-dokumantasyon/` — 389 kelime, TR+EN, 5 uç belgelenmiş, örnek JSON çıktısı,
  kullanım koşulları, "neden yayımlıyoruz" bölümü
- `/docs` ve `/docs/*` → **301** ile oraya yönleniyor (Pages `_redirects`)

### Uçların canlı durumu

| Uç | Durum | Boyut |
|---|---|---|
| /api/v1/prices | 200 | 647 KB |
| /api/v1/providers | 200 | 683 B |
| /api/v1/fx | 200 | 151 B |
| /api/v1/model-options | 200 | 86 KB |
| /models-index.json | 200 | 90 KB |

Bu uçlar zaten **statik dosya** olarak üretiliyor (9. turda eklenmişti); asıl eksik olan
belgelendirmeydi ve o da artık var.

---

## Madde 3 — Hesaplayıcıya e-posta toplama (haftalık maliyet raporu)

Uygulandı. Yerleşim: hesap yapıldıktan **sonra**, sonuç bloğunun altına — kullanıcı değeri
yeni görmüş, dönüşümün en yüksek olduğu an.

### Güvenlik ve KVKK

| Önlem | Uygulama |
|---|---|
| Çift onay (double opt-in) | `confirmed=0` ile yazılır; onay e-postasındaki bağlantı olmadan **tek e-posta bile** gönderilmez |
| Bot koruması | Cloudflare Turnstile, fail-closed (token yoksa 400) |
| Bal küpü | Gizli `website` alanı; doldurulursa sessizce yutulur |
| Açık rıza | Onay kutusu zorunlu, `consent_at` + `consent_text_version='v1'` saklanır |
| IP | Ham IP **saklanmaz**; SHA-256 kısaltılmış özet (spam kotası için) |
| Kota | Aynı IP'den günde 5 kayıt |
| Tek tıkla çıkış | `unsubscribe_token`, `unsubscribed_at` işaretlenir (kayıt silinmez) |

### Eklenen dosyalar

```
functions/api/bulten.js         POST — kayıt + onay e-postası
functions/api/bulten-onay.js    GET  — çift onayın 2. adımı
functions/api/bulten-iptal.js   GET  — tek tıkla çıkış
db/newsletter.sql               D1 şeması (uygulandı)
```

### Canlı doğrulama

```
POST /api/bulten  (Turnstile yok)        -> HTTP 400  ✓ reddetti
POST /api/bulten  (onay kutusu yok)      -> HTTP 400  ✓ reddetti
POST /api/bulten  (geçersiz e-posta)     -> HTTP 400  ✓ reddetti
GET  /api/bulten-onay (geçersiz token)   -> HTTP 400  ✓ reddetti
D1 newsletter_subscribers                -> 0 satır  ✓ geçersiz istek yazılmadı
```

### JS'siz çalışma

Form `fetch` ile gönderilir; JavaScript kapalıysa klasik POST devreye girer ve
`Accept: text/html` başlığını gören uç HTML teşekkür sayfası döner.

---

## Canlı kabul testi

```
PASS 200 /api-dokumantasyon/ (17.4 KB)
PASS 301 /docs -> /api-dokumantasyon/
PASS 200 /robots.txt (311 B)
PASS 200 /hesaplayici/ (132.7 KB, bülten formu dahil)
PASS 200 /en/hesaplayici/ (132.1 KB)
PASS 200 /api/v1/prices · /api/v1/fx · /api/v1/providers · /api/v1/model-options
PASS 200 /sitemap.xml
```

**Testler: 286 geçiyor, 6 atlandı** (7 yeni test bu turda eklendi).

---

## Not: "Ücretsiz araç + bülten + API = trafik → para hattı"

Bu formülün üç ayağı da artık ayakta. Ancak dürüst bir uyarı:

- Liste **sıfır abone** ile başlıyor; haftalık raporun gönderilmesi için ayrı bir zamanlanmış
  iş (GitHub Actions + `sendMailBatch`) gerekir. Bu turda **toplama altyapısı** kuruldu,
  gönderim işi kurulmadı — abone birikmeden gönderim işi kurmak boşa kod olurdu.
- Gerçek gelir için hâlâ **sizin başvurunuz** gerekiyor: AdSense yayıncı kimliği ve
  affiliate programları (`AFFILIATE_*`).
- Bülten, arama motoru trafiğini **tekrar ziyarete** çevirir; kendi başına trafik üretmez.
  Trafik üreten kısım SEO (bookmark'lanabilir araç sayfaları) ve API'nin keşfedilmesi.
