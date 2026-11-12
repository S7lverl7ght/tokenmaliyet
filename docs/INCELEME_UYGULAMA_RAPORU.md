# İnceleme Raporu — Uygulanan Geliştirmeler

Kaynak: `TokenMaliyet Site İnceleme ve Geliştirme Raporu` (11.11.2026)
Uygulama: 11–12.11.2026 · **91 test geçiyor**

## Kritik bulgular — hepsi ele alındı

### 1. Fiyat ölçek hataları ✅
Rapor "girdi/çıktı arasında 1000 kata yakın fark" diyordu. Kaynağı doğruladım:
**bizim hatamız değildi** — OpenRouter API'si `z-ai/glm-5.2` için prompt `7e-09`, completion
`6.8e-06` veriyor (971 kat). Ama rapor haklıydı: bu yayınlanmamalı.

**Yapılan:** QA katmanına iki kural eklendi:
- `output_input_ratio` — token fiyatlarında çıktı/girdi oranı 0,3–30 aralığı dışındaysa **yayınlanmaz**
- `batch_not_premium` — batch varyantı normal fiyattan pahalı olamaz

**Sonuç:** 18 gözlem (10 model) reddedildi: glm-5.2 (971×), deepseek-v4.1-flash (83×), kimi-k3 (83×)…
Eşik 50 → **%30**'a indirildi.

### 2. Varsayılan sıralama ✅
İlk ekran artık tanınmayan pazaryeri modelleriyle dolmuyor. Yeni varsayılan **"Önerilen"**:
doğrudan sağlayıcılar önce (OpenAI, Anthropic, Gemini, DeepSeek), sonra fiyat.

### 3. Üç ondalık yazım ✅
`13,860 USD` → `13,86 USD`. Yeni `price_digits()` kuralı:
≥1 → 2 ondalık, ≥0,1 → 3, ≥0,01 → 4, altı → 6. TRY karşılıkları da aynı kurala uyuyor.

### 4. Türkçe token farkı — **artık ürün** ✅
Raporun "asıl farklılaşma burada" dediği nokta ölçüldü ve sayfaya dönüştü.

**Ölçüm (gerçek tokenizer, `tiktoken` cl100k_base, 8 cümle çifti):**
- Türkçe: **215 token** · İngilizce: **92 token** → **2,34×** (%134 fazla)
- Türkçe 2,48 karakter/token · İngilizce 5,95 karakter/token
- En uç örnek: "Önbellek kullanımı, uzun bağlamlı uygulamalarda maliyeti önemli ölçüde düşürür." → **3,45×**

Yeni sayfa: **`/turkce-token-maliyeti`** — ölçüm tablosu, maliyet hesaplayıcı (TR/EN farkı),
"neden oluyor" açıklaması. Sitenin en güçlü SEO ve paylaşım içeriği.

### 5. Yasal sayfalar ✅
**`/gizlilik`** (KVKK aydınlatma + çerez + sorumluluk reddi), **`/iletisim`**,
**`/duzeltmeler`** (kamuya açık değişiklik kaydı). Altbilgiye üçü de eklendi.
"Reklam ve izleme çerezi kullanılmaz" notu görünür.

## Diğer iyileştirmeler

| Bulgu | Yapılan |
|---|---|
| Aynı model iki satırda, batch pahalı | `batch_not_premium` QA kuralı; varyantlar alt modelde etiketli |
| GPU alt liste etiketsiz | Her satıra tip, GPU modeli, VRAM, minimum kiralama eklendi |
| GPU "en düşük" tanımsız | Açıklama tablo üstüne taşındı; on-demand varsayılan, spot ayrı satır |
| GPU fiyat aralığı tekrarı | `13,86 – 13,86` yerine tek değer |
| Saatlik fiyat TL'si yok | Aylık (730 saat) TL eklendi |
| Hesaplayıcıda cache yok | Önbellek oranı seçici (0/25/50/75), cache fiyatı varsa hesaba katılır |
| Hesaplayıcıda grafik yok | İki modeli karşılaştıran çubuk grafik |
| Boş forma bakan kullanıcı | 5 hazır senaryo (destek botu, kod asistanı, özetleme, içerik, RAG) |
| Karşılaştır boş açılıyor | Açılışta 2 farklı model seçili, örnek sonuç görünür; 3–4 boş |
| Rehberler aynı tarihli | Yayın + güncelleme ayrı; yazar eklendi; her yazıya "bunu hesapla" bağlantıları |
| Hakkında yinelenen kaynaklar | Sağlayıcı başına tek satır, ikincisi "yedek" olarak |
| Yayıncı/iletişim yok | "Yayıncı ve iletişim" bölümü eklendi |
| Sütunlar sıkışıyor | "Model sayfası" kolonu yeniden boyutlandırıldı |
| Düşük kontrast (koyu tema) | Birincil buton `#818CF8` + beyaz = **2,98:1**. `--on-primary` token'ı ile **7,5:1**'e çıkarıldı |

## Doğrulama

```
91 passed, 1 warning in 2.11s
```

Kontrast denetimi (7 sayfada, tarayıcıda ölçüldü): **0 ihlal**.
12 rota 200 döndürüyor.

## Yapılmayanlar (bilinçli)

- **"Karşılaştır" ve "Hesaplayıcı"yı birleştirme** — rapor öneriyor; ama ikisi farklı zihinsel
  model (biri "hangi model daha ucuz", diğeri "benim faturam ne olur"). Birleştirmek yerine
  ikisini birbirine bağladım (model detayından her ikisine geçiş). Talep gelirse birleştirilir.
- **Çoklu dil arayüzünü kaldırma** — rapor "Türkçe trafik tezi doğrulanana kadar İngilizceyi
  ekleme" diyor; zaten yalnızca gezinme/etiket düzeyinde, maliyetsiz.
- **Kalite/benchmark puanı** — raporun uyarısına uyuldu, eklenmedi.
- **"Uygula" düğmesini kaldırma** — filtrelerin anında çalışması JS gerektirir; JS'siz
  çalışabilirlik korundu (progressive enhancement). Bu bir tercih, eksik değil.

## Not

Bir hata yaptım ve düzelttim: şablonlara toplu regex uygularken (PowerShell `-replace`)
16 HTML dosyası bozuldu. Kurtarma deseniyle tamamı geri yüklendi; sonrasında tüm değişiklikler
Python/Node ile, doğrulama adımlarıyla yapıldı. 91 test bunu doğruluyor.
