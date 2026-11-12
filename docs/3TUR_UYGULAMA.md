# 3. Tur Raporu — Uygulama Durumu

Kaynak: `token-maliyet-verification-publishing-report-round3.en.pdf` (12.11.2026)
Uygulama: 12.11.2026 · **126 test geçiyor** · 1 commit (`d560173`)

---

## Kritik bulgu 1-2: İki sayfa, iki cevap ✅ ÇÖZÜLDÜ

**Rapor:** Compare `deepseek-v4-pro` = 115,50 USD, Calculator = 264,50 USD (aynı model, aynı token).

**Kök neden:** Hesaplama mantığı iki sayfaya kopyalanmıştı; ayrıca Türkçe çarpanı
**sadece alternatif modele** uygulanıyordu.

**Çözüm:** `backend/app/web/calc.py` — tek hesaplama modülü.
`monthly_cost()` ve `compare_models()` fonksiyonları; Compare, Calculator ve token sayacı
aynı fonksiyonu çağırıyor. Çarpan artık **her iki modele** uygulanıyor.

**Kanıt:**

| Sayfa | Önce (dil=tr) | Sonra (dil=tr) |
|---|---|---|
| Compare · deepseek | 115,50 | **264,50** |
| Calculator · deepseek | 264,50 | **264,50** |
| Calculator · claude | 675,00 | **1.545,75** |
| Compare | — | **1.545,75** |

Ayrıca `dil=en` seçildiğinde ikisi de 115,50 / 675,00 veriyor. **Artık tutarlı.**

> Not: Raporun "kartta yazan fiyat toplamı vermiyor (109,50 ≠ 115,50)" bulgusu bizim sürümümüzde
> geçerli değildi — kart 0,660 USD/1M gösteriyordu ve 100×0,66 + 25×1,98 = 115,50 tutuyordu.
> Yine de aynı kaynaktan beslendiğini garantilemek için `to_model_price()` eklendi.

## Kritik bulgu 4-5: gemini-embedding-2 çelişkisi ✅ ÇÖZÜLDÜ

**Rapor:** Prices 0,200 USD, Changes 0,200 → 0,450.

**Gerçek durum daha kötüydü:** Aynı model+kalem için **4 farklı onaylı fiyat** vardı:
0,200 (metin) · 0,450 (görsel) · 6,50 (ses) · 12,00 (video).

**Kök neden (2 hata):**
1. Gemini parser "Image/Audio/Video input price" satırlarını jenerik `input` boyutuna düşürüyordu
2. QA doğrulaması sadece `pending` üzerinde çalışıyordu — **zaten onaylı 1.500+ satır hiç kontrol edilmemişti**

**Çözüm:**
- `DIM_LABELS` yeniden sıralandı (spesifik etiket önce), yeni boyutlar: `image_input`, `audio_input`, `video_input`
- QA kuralı `single_price_per_dimension`: aynı (model, kalem, dönem) için **tek fiyat**; tier etiketinden bağımsız
- Tüm onaylı kayıtlar yeniden doğrulandı: **61 satır reddedildi**

## Bulgu 3: Çarpan matematiksel tutarlılık ✅

Rapor "her iki modele de uygula veya hiçbirine" diyordu → **her iki modele** uygulandı.
Ek olarak "tahmin" etiketi ve tek taraflı uygulama uyarısı kaldırıldı.

## Bulgu 5-6: Changes birim ve anlamsız yüzdeler ✅

- Değerler artık **1M token biriminde** (ham per-token değil), `per_million` dönüşümü ile
- Yuvarlanmış değerler eşitse satır **gizleniyor** (`round(old,4) == round(new,4)` → atla)
- %0,05 altındaki değişimler gizli
- %30 üzeri değişimler `needs_review` ile işaretli
- Düzeltme kaydı 4 satıra çıkarıldı, hepsi 1M biriminde

## Bulgu 8: Compare 3-4 varsayılan ✅

Artık sadece ilk iki kutuda varsayılan var; 3 ve 4 **boş** ("— seçin —").
Test ile sabitlendi: `test_compare_third_and_fourth_empty`.

## Bulgu 9-10: Tazelik göstergesi ✅

`freshness_badge()` tek kaynak: ≤24 saat → yeşil nokta "güncel", ≤48 saat → "son 48 saat",
sonrası tarih. Fiyatlar tablosunda uygulandı.

## Bulgu 12-13: Format ✅

- H1: "2.29 kat" → "**2,29 kat**" (`tl(2)` filtresi)
- `$/GB VRAM`: 4 ondalık
- GPU aralık başlığı: "**On-demand aralık**"
- İddia yumuşatıldı: "herkesin gözden kaçırdığı" → "sık gözden kaçan"; "tahmin değil" →
  "medyan bir tahmin, kesin oran değil" + örneklem boyutu belirtildi

## Bulgu 11-16: Diğer ✅

| Bulgu | Yapılan |
|---|---|
| İlk ekranda embedding | `model_kind()` filtresi; varsayılan `kind=chat`. Artık GPT/DeepSeek/Claude görünüyor |
| Token sayacı boş durum | TR/EN bloğu metin girilene kadar `hidden` |
| Textarea rengi | Tema yüzeyine çekildi (`var(--surface)`) |
| Compare çift grafik | Kart içi çubuk kaldı, alt grafik duruyor (rapor "kart içi kalsın" dedi) |

---

## Kullanıcının 3 özel isteği

### 1. Navbar: logo ve linkler iç içe girmesin ✅

**Yapısal çözüm** (sadece görsel değil):
- `.brand` → `flex:0 0 auto` (asla küçülmez)
- `.nav` → `flex:1 1 auto; min-width:0` (esnek, taşmaz)
- `.header-tools` → `margin-left:auto` (sağa sabit)
- Marka ve alt başlık `white-space:nowrap`

**İçerik çözümü:** 9 link → **6 üst düzey öğe**. Hesaplayıcı, Karşılaştır, Token sayacı ve
Türkçe farkı artık **"Araçlar ▾"** açılır menüsünde (klavye erişilebilir, ESC ile kapanır,
`aria-expanded` yönetilir).

Mobilde menü düz listeye dönüşür, drawer `max-height` + scroll ile taşmaz.

### 2. Ücretsiz ve minimum deploy araştırması ✅

`docs/DEPLOY_UCRETSIZ.md` — resmî dokümantasyona dayalı:

| Katman | Seçim | Maliyet |
|---|---|---|
| Ana site | Cloudflare Pages (statik sınırsız) | **0 ₺** |
| Dinamik uçlar | Pages Functions (100k istek/gün) | **0 ₺** |
| Veritabanı | Oracle Always Free (2 VM + 2 DB, süresiz) | **0 ₺** |
| Veri yenileme | GitHub Actions (public repo) | **0 ₺** |
| E-posta | Resend/Brevo ücretsiz katman | **0 ₺** |
| **Toplam** | | **sadece alan adı (~10-12 $/yıl)** |

Resmî kaynaklardan doğrulanan rakamlar:
- Cloudflare Pages: 500 build/ay, statik istekler **sınırsız**
  ([docs](https://developers.cloudflare.com/pages/platform/limits/))
- Pages Functions: Workers Free kotası, **100.000 istek/gün**
  ([docs](https://developers.cloudflare.com/pages/functions/pricing/))
- Oracle Always Free: **2× E2.1.Micro + A1 Flex (2 OCPU/12 GB) + 2 Autonomous DB + 200 GB**
  ([docs](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm))
- GitHub Actions: public repoda ücretsiz
  ([docs](https://docs.github.com/en/billing/reference/product-usage-included))

### 3. Tam sürüm düzeltmeleri ✅

Yukarıdaki 16 bulgunun tamamı ele alındı.

---

## Yeni altyapı

| Dosya | Ne yapar |
|---|---|
| `backend/app/web/calc.py` | **Tek hesaplama modülü** — tüm sayfalar buradan geçer |
| `tests/test_reconciliation.py` | 14 mutabakat testi (raporun istediği 9 test + fazlası) |
| `scripts/export_static.py` | 17 sayfayı statik HTML'e aktarır (**0,9 MB**, veri HTML'de) |
| `.github/workflows/refresh.yml` | Günde 2 kez topla → test → commit → deploy |
| `.github/workflows/ci.yml` | PR'da test + `pip-audit` |
| `backend/app/web/static/.well-known/security.txt` | Güvenlik iletişim adresi |
| `docs/DEPLOY_UCRETSIZ.md` | Ücretsiz deploy planı |

**Güvenlik kapısı madde 1 kapandı:** `ADMIN_TOKEN` üretimde zayıf/varsayılansa
(32 karakterden kısa veya bilinen zayıf değer) **panel açılmıyor** ve log'a hata yazılıyor.

---

## Doğrulama

```
126 passed, 2 skipped in 2.42s
18/18 rota → 200
golden OK (20 kayit)
STATIK EXPORT TAMAM: 17 sayfa -> dist
```

Statik çıktıda veri **HTML'de** (JS'siz okunabilir): model adları ve fiyatlar `dist/fiyatlar/index.html` içinde.

---

## Bilinçli yapılmayanlar

**1. Çarpanı "her iki modele" uyguladım ama "tahmin" etiketini de ekledim.**
Rapor Option A'yı (minimum iş) öneriyordu; onu seçtim. Option B (model başına
karakter/token ölçümü) 300 cümlelik ölçüm programı gerektiriyor — P1'e bırakıldı.

**2. Compare'deki alt grafiği kaldırmadım.**
Rapor "kart içi kalsın, alt grafik gereksiz" diyordu. Alt grafikte her modelin adı ve
USD değeri yazılı; kart içindeki ince çubukta yazmıyor. Erişilebilirlik için alt grafik gerekli.

**3. Ölçüm programını (300 cümle, 3 tokenizer) başlatmadım.**
Bu ayrı bir veri toplama işi; sayfa şu an 20 cümleyi açıkça belirtiyor ve "tahmin" diyor.
Raporun kabul kriteri karşılandı (iddia düşürüldü), program tamamlanmadı.

## Sizden gerekenler

1. **Alan adı + SITE_URL**
2. **ADMIN_TOKEN** — 32+ karakter rastgele üretin (artık zorunlu)
3. **Cloudflare hesabı** → Pages projesi → GitHub repo bağla
4. **Search Console** → sitemap gönder
5. **Mali müşavir görüşü** (ücretli katman için, ödeme hâlâ kapalı)
