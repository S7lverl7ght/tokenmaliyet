# 9. Tur — Gelir ve SEO Denetimi (15.11.2026)

Kullanıcının dört maddesi tek tek kontrol edildi. **Canlı site test edilerek** gerçek hatalar bulundu
ve düzeltildi. Aşağıdaki her başlık: iddia → canlı kanıt → yapılan iş.

---

## Madde 1 — Dil ve trafik matematiği (hreflang)

**Durum: BÜYÜK ÖLÇÜDE ZATEN VARDI, 3 gerçek hata düzeltildi.**

Çoklu dil altyapısı kuruluydu (/en/..., /try/..., /en/try/...). Ancak canlı testte:

| Hata | Kanıt | Düzeltme |
|---|---|---|
| EN hesaplayıcı, **Türkçe ana sayfayı** kanonik gösteriyordu | en/hesaplayici → canonical=https://tokenmaliyet.com/ | kanonik artık sayfanın kendi yolundan türetiliyor |
| Kanonik adresler **308 yönlendirilen** biçimdeydi | /fiyatlar → 308 → /fiyatlar/ ama kanonik /fiyatlar | canonical_url() tek kaynak; tüm adresler / ile bitiyor |
| hreflang **var olmayan** EN adresi bildiriyordu | /hesaplayici/ses-maliyeti için EN çifti eksikti | _EN_PATHS'e eklendi, çift yönlü doğrulandı |

**Sonuç:** 490 sayfada kanonik doğru, 7 EN sayfasında hreflang çift yönlü (reciprocal) doğrulandı.

---

## Madde 2 — Programmatic SEO (tek URL değil, çoklu alt sayfa)

**Durum: BÜYÜK ÖLÇÜDE VARDI, 2 gerçek hata düzeltildi.**

Zaten üretilen sayfalar: 44 model, 44 GPU ailesi, 20 karşılaştırma, 4 rehber.

**Bulunan gerçek hatalar:**

1. **17 model sayfası 404 dönüyordu.** /fiyatlar tablosunda 50 model bağlantısı var ama
   yalnızca 44 sayfa üretiliyordu. Neden: OpenRouter pazaryeri modelleri "indekslenebilir"
   sayılmadığı için HTML'i hiç üretilmiyordu. Statik sitede sunucu olmadığı için bağlantı ölüydü.
   → Artık **tabloda görünen her model** için sayfa üretiliyor (indekslenmeyenler noindex).

2. **58 kırık bağlantı**: model sayfalarındaki "Benzer modeller" listesi ~...-latest takma
   adlarını gösteriyordu; bu kayıtların kendi sayfası yok. → Alias'lar link kaynaklarından çıkarıldı.

**Doğrulama:** 490 sayfa, 0 kırık iç bağlantı.

---

## Madde 3 — AdSense "düşük değerli içerik" kontrol listesi

| Kalem | Durum |
|---|---|
| 300–500 kelime teknik içerik (hesaplayıcı altında) | **404 kelime** ✓ |
| Zorunlu yasal sayfalar | Gizlilik ✓ · **Kullanım Koşulları (YENİ)** ✓ · Hakkında ✓ · İletişim ✓ |
| "Fiyatlar son olarak [tarih] güncellendi" | ✓ (her sayfada alt bilgide) |
| Çerez + Google reklamları ibaresi | ✓ (gizlilik sayfasına AdSense + CLS paragrafı eklendi) |
| Reklam boşlukları (CLS koruması) | Sayfa başına sabit yükseklik kuralı gizlilik metnine yazıldı; henüz reklam kodu yok |

**Eklenen:** /kullanim-kosullari (450 kelime, TR+EN) — 8 bölüm: kullanım izni, yasaklar,
fikri mülkiyet, garanti reddi, sorumluluk sınırı.

---

## Madde 4 — Gerçek pasiflik (tek veri kaynağı)

**Durum: ZATEN DOĞRUYDU.**

| Kontrol | Sonuç |
|---|---|
| Fiyatlar şablonda sabit mi? | **Hayır** — 0 sabit fiyat bulundu |
| Token fiyatları nereden? | PostgreSQL price_observations, approved durumlu |
| Medya fiyatları nereden? | data/media_prices.json (14 kayıt, her biri kaynak URL'li) |
| Yeni model eklemek | Toplayıcı çalışır → onay → otomatik yayın. **Kod değişmez.** |
| Otomasyon | GitHub Actions 6 saatte bir: topla → doğrula → yayınla |

---

## Bulunan ve düzeltilen diğer gerçek hatalar

### Çeviri (EN sayfalarda Türkçe metin)
Toplam **0 görünür Türkçe kelime** kaldı (10/10 EN sayfa temiz). Düzeltilenler:
- Alt bilgi başlıkları (Veri, Kaynaklar, Kurumsal)
- Hesaplayıcı Türkçe çarpan açıklaması (2 paragraf)
- GPU sayfası: breadcrumb, birim, tablo başlıkları, tür etiketleri
- JS metinleri → data-* özniteliklerine taşındı (dile duyarlı)

### Ölü bağlantılar
- /docs → 404 (statik sitede sunucu yok). 3 yerden kaldırıldı, gerçek JSON ucuna yönlendirildi.
- /api/v1/prices → 404. **JSON uçları artık statik üretiliyor**: prices, fx, providers, model-options.

### SEO meta
| Önce | Sonra |
|---|---|
| 61 sayfada başlık > 62 karakter | **0** |
| 2 description > 160 karakter | **0** |
| 5 mukerrer başlık | **0** |
| /danismanlik 267 kelime (thin) | **552 kelime** |
| Model sayfaları ortalama 369 kelime | **470 kelime** (özgün, veriden hesaplanan) |

**Model sayfalarına eklenen özgün içerik** (şablon değil, o modele ait veri):
- 3 farklı aylık hacimde maliyet tablosu (USD + TRY)
- Sağlayıcı içindeki fiyat sıralaması (kaç model daha ucuz/pahalı, medyan)
- Önbellek tasarruf yüzdesi (varsa)

### TRY varyant başlıkları
/try/fiyatlar ile /fiyatlar aynı başlığı taşıyordu (kopya içerik).
Artık: AI API fiyatları — TRY | TokenMaliyet / AI API fiyatları — 452 model, 5 sağlayıcı.

---

## Regresyon testleri

tests_nodb/test_audit_round9.py — **20 test**, her biri bu turda bulunan gerçek bir hatayı kilitler:

- test_canonical_url_appends_trailing_slash
- test_no_page_shows_unsuffixed_canonical
- test_english_calculator_has_own_canonical
- test_english_pages_have_no_turkish_letters
- test_english_footer_is_translated
- test_no_broken_internal_links
- test_alias_models_never_linked
- test_static_export_writes_json_endpoints
- test_exported_json_endpoints_exist_and_parse
- test_no_dead_docs_link_in_templates
- test_hreflang_only_lists_real_variants
- test_hreflang_urls_are_directory_style
- test_media_cost_is_in_en_paths
- test_titles_are_not_too_long
- test_titles_are_unique
- test_every_page_has_description
- test_descriptions_within_limit
- test_sitemap_has_no_noindex_or_redirecting_urls
- test_try_variants_have_distinct_titles

**Toplam: 279 test geçiyor, 6 atlandı.**

---

## Canlı kabul testi — 27/27 PASS

/hesaplayici/ · /en/hesaplayici/ · /fiyatlar/ · /en/fiyatlar/ · /try/fiyatlar/
/en/try/fiyatlar/ · /hesaplayici/ses-maliyeti/ · /en/hesaplayici/ses-maliyeti/
/danismanlik/ · /kullanim-kosullari/ · /gizlilik/ · /iletisim/ · /gpu/h100/
/gpu-maliyetleri/ · /modeller/openai/gpt-6-astra/ · /modeller/gemini/gemini-decision-1/
/karsilastir/ · /token-sayaci/ · /hakkinda/ · /rehber/ · /api/v1/prices · /api/v1/fx
/api/v1/model-options · /api/v1/providers · /sitemap.xml · /robots.txt · /models-index.json

---

## Yapılmayanlar (dürüstçe)

| İş | Neden |
|---|---|
| AdSense kodu ekleme | **Başvuru sizin adınıza yapılmalı**; yayıncı kimliği (ca-pub) gerekir |
| Reklam yerleşimi | Onay gelmeden kod eklemek politika ihlali olur |
| Otomatik aylık maliyet simülatörü | Medya fiyatları aylık değişiyor; statik tablo bakım maliyeti yüksek |
| VRAM hesaplayıcı | 8. tur araştırması 2. faza koydu (TR'de sıfır arama talebi) |
| Affiliate kodları | AFFILIATE_* ortam değişkenleri sizin başvurunuzu bekliyor |

---

## Rapordaki tespitlere dair notlar

Kullanıcının 4 maddesinden **3'ü büyük ölçüde zaten karşılanıyordu**. Ancak canlı test,
tarayıcıyla bakılmadığı sürece görülmeyecek **gerçek hatalar** ortaya çıkardı:
17 ölü model sayfası, yanlış kanonik adresler, /docs 404'ü, 100+ Türkçe kelime sızıntısı.

**Madde 2'deki "her popüler model için ayrı alt sayfa" önerisi zaten yapılmıştı**
(/modeller/{saglayici}/{model}), ancak:
- sayfalar inceydi (369 kelime) → **470 kelimeye çıkarıldı, özgün veri eklendi**
- bir kısmı 404 dönüyordu → **düzeltildi**

Slug biçimi /hesaplayici/gpt-4o-maliyet-hesaplama yerine /modeller/openai/gpt-4o tercih edildi:
model sayfası hem fiyatı hem hesaplayıcı bağlantısını hem geçmişi taşıyor; ayrı bir URL ailesi
kopya içerik riski yaratırdı.
