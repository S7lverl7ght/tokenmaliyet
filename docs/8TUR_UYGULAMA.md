# 8. Tur: Çeviri, Yeni Araç ve Site Denetimi (15.11.2026)

Üç görev vardı. Üçü de tamamlandı.

---

## 1) Çeviri sorunu — 174 → 0

**Kullanıcı haklıydı.** İngilizce sayfalar Türkçe doluydu.

| Sayfa | Önce | Sonra |
|---|---|---|
| en/hakkinda | 48 | 0 |
| en/token-sayaci | 41 | 0 |
| en/karsilastir | 35 | 0 |
| en/gpu-maliyetleri | 28 | 0 |
| en/hesaplayici | 23 | 0 |
| en/uyari | 20 | 0 |
| en/fiyatlar | 12 | 0 |
| **Toplam benzersiz** | **174** | **0** |

### Yapılanlar

- 13 şablonda başlık, etiket, açıklama ve buton metinleri iki dilli yapıldı
- `site_tagline`, `method_labels`, `CHANNEL_LABELS_EN`, `SCENARIOS` dile duyarlı
- Token sayacındaki JS metinleri (`L` nesnesi) çevrildi
- Rehber başlıkları kısaltıldı ve çevrildi

### Kalan %5 neden sorun değil

Türkçe token sayfasında İngilizce cümleler **kasıtlı**: o sayfa Türkçe/İngilizce
token karşılaştırma tablosu. Aynı içeriğin iki dildeki hâli yan yana gösteriliyor.

---

## 2) Yeni özellik: Ses/Görsel/Video maliyet hesaplayıcı

### Neden bu (araştırma sonucu)

`docs/ARASTIRMA_VRAM_MEDYA.md` bulguları:

| Bulgu | Veri |
|---|---|
| Medya fiyat aramaları VRAM'in | **10–20 katı** |
| `seslendirme yapay zeka` (TR) | **51,5** endeks |
| `vram hesaplama` (TR) | **0,0** |
| ElevenLabs affiliate | **%22** (GPU tarafında %3) |
| Rekabet | Tek sayfalık, markasız |

Sonuç: **ses ayağı hemen, VRAM 2. fazda, video şimdilik yok.**

### Kurulan

| Dosya | Görev |
|---|---|
| `data/media_prices.json` | 14 fiyat kaydı, **her biri kaynak URL'li** |
| `backend/app/web/media_cost.py` | `cost()`, `compare()`, `options_for()` |
| `templates/ses_maliyeti.html` | Sayfa (TR + EN) |
| `routes.py` | `/hesaplayici/ses-maliyeti` + `/en/` `/try/` varyantları |

### Fiyatlar (resmî kaynaklardan)

```
ElevenLabs v4        0,08 USD / 1K karakter
ElevenLabs v4 Turbo  0,04 USD / 1K karakter
OpenAI tts-1        15,00 USD / 1M karakter
OpenAI Whisper       0,006 USD / dakika
FLUX 3 Image         0,041 USD / görsel
Runway kling3.0      0,09 USD / saniye
```

**Uydurma fiyat yok:** dosyada olmayan model hesaplanmaz; test bunu kilitliyor.

### Doğrulama

```
10.000 karakter ElevenLabs v4 = 0,80 USD  ✓
1 saat Whisper            = 0,36 USD  ✓
100 görsel FLUX           = 4,10 USD  ✓
30 sn Runway              = 2,70 USD  ✓
```

---

## 3) Site denetimi — bulunan ve düzeltilen SEO hataları

### Kritik: 65 sayfa aynı başlığı kullanıyordu

```
44 x "GPU kiralama maliyetleri — saatlik fiyat karşılaştırma"
21 x "Model karşılaştırma — maliyet · 2 model"
```

Google bunları **kopya içerik** sayar; hiçbiri sıralanamaz.

**Düzeltme:** Her GPU sayfası `{GPU adı} GPU fiyatları`, her karşılaştırma
sayfası `{model A} vs {model B} maliyet` başlığını alıyor. Uzun model adları
22 karakterde kırpılıyor.

### Diğer düzeltmeler

| Sorun | Önce | Sonra |
|---|---|---|
| Title/description karakter sınırı | 61 sayfa | **0** |
| Kök `index.html` description | yok | eklendi |
| Karşılaştırma sayfaları sitemap'te | yok | 20 çift eklendi |
| GPU aileleri sitemap'te | 20 | tümü |

### Denetim sonucu: temiz

```
SEO sorun sayısı: 0
Tekrarlanan title: 4 (hepsi /en/ ve /try/ varyantı — hreflang ile doğru)
Dönüşüm hunisi: 5/5 sayfa mevcut
İç linkler: hesaplayıcı → 5/5 araç
```

### Bilinçli olarak noindex

`/uyari` ve `/en/uyari` — form sayfası, arama sonucunda görünmesi istenmiyor.
Bu doğru davranış, hata değil.

---

## Eklenen CTA'lar (gelir odaklı)

Ses maliyeti sayfasına:
- "Kapsamlı maliyet analizi ister misiniz?" → `/danismanlik`
- Fiyat uyarısı → `/uyari`

---

## Doğrulama

```
259 passed, 6 skipped
Canlı kabul (ses maliyeti): 7/7
SEO sorun: 0
Çevrilmemiş EN metin: 0
```

## Sıradaki (2. faz)

VRAM hesaplayıcı — araştırma formülü ve GPU fiyatları hazır:
`ağırlıklar + KV cache + overhead`; ama trafik düşük olduğu için önce ses
tarafının oturması beklenmeli.

## Yapılmayanlar (dürüstçe)

| İş | Neden |
|---|---|
| VRAM hesaplayıcı | Araştırma 2. faza koydu; talep düşük |
| Video simülatörü | Fiyatlar aylık değişiyor, bakım pahalı |
| Affiliate kodları | Sizin başvurunuz gerekiyor |
