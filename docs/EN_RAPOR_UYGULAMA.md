# Development and To-Do Report — Uygulama Durumu

Kaynak: `token-maliyet-development-and-todo-report.en.md` (11.11.2026)
Uygulama: 12.11.2026 · **114 test geçiyor** · 3 commit

---

## P0 — Bu hafta (tamamlandı)

| # | Madde | Durum | Kanıt |
|---|---|---|---|
| 1 | Veri doğruluk tablosundaki 10 madde | ✅ | Aşağıda tek tek |
| 2 | Varsayılan sıralama = popüler modeller + kaynak türü sütunu | ✅ | `default_models.py`, "Kaynak türü" kolonu |
| 3 | Açıklama "resmî sayfalar ve pazaryeri" | ✅ | `prices.html` lede metni |
| 4 | Gizlilik/KVKK, iletişim, sahip bilgisi | ✅ | `/gizlilik`, `/iletisim`, `/duzeltmeler`, Hakkında "Yayıncı" |
| 5 | Karşılaştır sayfasında 4 aynı varsayılan | ✅ | `default_models.py` tek kaynak; 3–4 boş |
| 6 | Search Console + sitemap | ⚠️ | Sitemap hazır (60 URL); **gönderim sizin** |
| 7 | Güvenlik başlıkları + XSS | ✅ | `test_security.py` (9 test) |

### Veri doğruluk tablosu — 10 maddenin karşılığı

| # | Rapor bulgusu | Gerçek durum | Yapılan |
|---|---|---|---|
| 1 | GPU B300 aralığı 8.990–13.260, listede max 12.050 | **Doğru tespit** — aralık gösterilmeyen satırdan geliyordu | Aralık artık **gösterilen** satırlardan hesaplanıyor |
| 2 | deepseek batch girdi > standart | **False positive** — iki farklı model karşılaştırılmış (v4.1-flash vs v4.1-flash-1017). Aynı modelde batch gerçekten %93 ucuz | `batch_not_premium` QA kuralı eklendi (yine de koruma var) |
| 3 | glm-5.2 girdi 0.007 / çıktı 6.80 (970×) | **Kaynakta böyle** — OpenRouter API'si bu değeri veriyor | `output_input_ratio` kuralı: 0,3–30 dışı **yayınlanmaz**. 18 gözlem reddedildi |
| 4 | `~deepseek-flash-latest` ve `deepseek-v4.1-flash-1017` aynı fiyat | **Doğru tespit** — alias | `mark_aliases()`: aynı fiyat imzası + "~" = alias, listede gizli |
| 5 | Açıklama "resmî sayfalar" ama ilk ekran pazaryeri | **Doğru tespit** | Açıklama düzeltildi + "Kaynak türü" kolonu + pazaryeri uyarı başlığı |
| 6 | GPU 3 ondalık "13,860" | **Doğru tespit** | `price_digits()`: ≥1 → 2, ≥0,1 → 3, ≥0,01 → 4, altı → 6 ondalık |
| 7 | Hesaplayıcı claude-sonnet-4.5, diğerleri fable-5 | **Doğru tespit** | `default_models.py` tek kaynak; üç sayfa aynı varsayılanı kullanıyor |
| 8 | Token sayacı 249 karakter → 75 token (3,3 char/token) iyimser | **Doğru tespit** | Türkçe ölçüm: **2,48 karakter/token**. Sayfada sapma ±%15/TR −%10…−%30 yazıyor |
| 9 | Kur kaynağı yok | **Doğru tespit** | `frankfurter.app` kaynağı + tarih her yerde; metodolojide açıklandı |
| 10 | GPU açılır listede spot/on-demand ayrımı yok | **Doğru tespit** | Her satıra tip, VRAM, min kiralama; ana tabloda on-demand varsayılan |

---

## P1 — 2–3. hafta

| Madde | Durum | Not |
|---|---|---|
| Hesaplayıcı + Karşılaştır birleştirme | ⚠️ **Kısmi** | Birleştirmedim; bunun yerine TR çarpanı + senaryolar + karşılıklı bağlantı. Gerekçe aşağıda |
| Türkçe token çarpanı | ✅ | **2,29×** (20 cümle, aralık 1,77–3,57). Hesaplayıcıda `dil=tr` seçeneği |
| Token sayacında TR/EN karşılaştırması + sapma | ✅ | "Türkçe mi, İngilizce mi?" bloğu + ölçülmüş sapma |
| Doğrulama kuralları kodda + golden test | ✅ | 5 kural; `tests/golden_prices.json` (20 kayıt) + `scripts/check_golden.py` |
| GPU filtre/sıralama/tip/$-GB/aylık | ✅ | Sağlayıcı + fiyat türü + sıralama; $/GB VRAM; aylık ₺ |
| "Bu hafta ne değişti" + changelog | ✅ | `/degisiklikler` (fiyat değişimleri + düzeltmeler) |
| İlk 3 derin rehber | ✅ 1/3 | "API mi kendi GPU mu?" eklendi (gerçek veriyle). Diğer ikisi mevcut |
| E-posta uyarı formu | ✅ | `/uyari` — KVKK açık rıza, çift onay, eşik/yön seçimi |
| Affiliate linkler | ⛔ **Yapılmadı** | Program başvurusu sizin; kod tarafı hazır değil (bilinçli) |
| Dataset/Breadcrumb/Article schema + noindex | ✅ | 4 sayfa tipinde doğrulandı, JSON-LD geçerli |

---

## P2 — 4–8. hafta

| Madde | Durum |
|---|---|
| 30–50 popüler model için özgün sayfa | ✅ Sitemap 406 → **44 model sayfası**; gerisi `noindex` |
| Türkiye'deki GPU sağlayıcıları | ⛔ Veri kaynağı yok (uydurma fiyat yazmam) |
| API vs GPU başabaş hesaplayıcı | ✅ Rehber olarak (interaktif değil) |
| Pricing sayfası + bekleme listesi | ⛔ Mali müşavir onayı olmadan ödeme açılmıyor |
| CSV/JSON indirme, embed | ⛔ |
| 5–6 ek rehber | ⚠️ 4 rehber (1 yeni) |
| İngilizce sürüm + hreflang | ⚠️ Arayüz TR/EN var; içerik çevrilmedi |

---

## Bilinçli yapılmayanlar (gerekçeli)

**1. Hesaplayıcı ve Karşılaştır'ı birleştirmedim.**
Rapor "aynı soruyu yanıtlıyor" diyor; katılmıyorum. Hesaplayıcı "benim faturam ne olur",
Karşılaştır "hangi model daha ucuz" sorusunu yanıtlıyor — farklı zihinsel model.
Onun yerine: TR çarpanı, 5 hazır senaryo, önbellek oranı, çubuk grafik ve karşılıklı bağlantı ekledim.
Talep gelirse birleştirilebilir.

**2. Affiliate link koymadım.**
Program başvurusu yapılmadan link koymak, olmayan bir ortaklığı ima eder. Yapısal hazırlık
(`rel="sponsored"` desteği) eklenebilir ama program onayı sizin tarafınızda.

**3. Ödeme/abonelik açmadım.**
Rapor da aynı şeyi söylüyor: mali müşavir görüşü olmadan ücretli abonelik başlatılmamalı.
E-posta listesi (ücretsiz) bunun ön adımı olarak hazır.

**4. Türkiye'deki GPU sağlayıcıları eklemedim.**
Doğrulanabilir, otomatik çekilebilir bir kaynak bulamadım. Uydurma fiyat yazmak sitenin
tek varlığını (güven) yok eder. Elle girilecek kaynak listesi verirseniz eklerim.

---

## Golden testin yakaladığı gerçek hata

Raporun "golden test tut" önerisi ilk gün işe yaradı:

**Bulgu:** `claude-haiku-5.5` için aynı kalemde iki farklı onaylı fiyat (0,125 ve 0,625).
**Kök neden:** Anthropic sayfası fiyatları **bağlam dilimine** göre ayırıyor
("Prompts ≤ 100K" / "> 100K"), parser bunu tek "standard" etiketiyle yazıyordu.
**Düzeltme:** Parser `priceBreakdown` seviyesini okuyor; her fiyat kendi dilim etiketiyle saklanıyor.
**Ek koruma:** `no_duplicate_dimension` QA kuralı — aynı model+kalem+dönem için iki farklı fiyat yayınlanamaz.

Bu hata, rapordaki 10 maddeden hiçbirinde yoktu; golden test olmasaydı canlıya çıkacaktı.

---

## Ölçülen değerler

| Metrik | Önce | Sonra |
|---|---|---|
| Test sayısı | 91 | **114** |
| Sitemap URL | 421 | **60** (44 derin model + 16 statik) |
| İndekslenebilir model sayfası | 406 | **44** |
| Türkçe token çarpanı | ölçülmemiş | **2,29×** (20 cümle, 1,77–3,57) |
| Golden test kaydı | 0 | **20** |
| XSS/güvenlik testi | 0 | **9** |

---

## Sizden gerekenler

1. **Search Console** — sitemap gönderimi (`/sitemap.xml`), mülk doğrulama
2. **ADMIN_TOKEN** — hâlâ `YerelAdmin2026-degistir`, canlıya çıkmadan değiştirin
3. **SITE_URL** — gerçek alan adı (canonical/OG/sitemap bunu kullanıyor)
4. **CONTACT_EMAIL** — `.env` içinde, şu an `iletisim@tokenmaliyet.com` varsayılan
5. **Affiliate programları** — başvuru ve onay
6. **Mali müşavir görüşü** — ücretli katman için (ödeme kasıtlı kapalı)
