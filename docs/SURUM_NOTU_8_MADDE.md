# TokenMaliyet — 8 Maddelik Değişiklik Özeti

Tarih: 11.11.2026

## 1. Kaynak bağlantısı düzeltildi

Her model satırındaki bağlantı artık **sağlayıcının kendi model sayfasına** gidiyor, ham JSON
datasetine değil:

| Sağlayıcı | Hedef |
|---|---|
| OpenAI | `platform.openai.com/docs/models/{slug}` |
| Gemini | `ai.google.dev/gemini-api/docs/models/{slug}` |
| OpenRouter | `openrouter.ai/{slug}` |
| Anthropic / DeepSeek | resmî model/pricing sayfası |

Kolon adı "Model sayfası" oldu; bilinmeyen sağlayıcıda fiyat sayfasına düşer.

## 2. GPU maliyetleri dolduruldu — 5 kaynak, gerçek veri

| Kaynak | Yöntem | Kalem |
|---|---|---|
| Runpod | resmî GraphQL API | 83 |
| DataCrunch | resmî fiyat tablosu | 42 |
| Lambda | resmî instance + cluster tablosu | 16 |
| Vast.ai | bundle API, doğrulanmış hostların medyanı | 8 |
| Hyperstack | resmî GPU sayfaları | 2 |
| **Toplam** | | **151 GPU-saat fiyatı, 5 sağlayıcı** |

Örnek çıktı: H100 **$2.89/saat**, H200 **$2.59**, B200 **$7.69**, RTX PRO 6000 **$0.50**.

**Veri kalitesi koruması:** varsayılan karşılaştırma on-demand fiyatıdır. On-demand medyanın
%35 altındaki spot/topluluk teklifleri elenir (ör. Runpod H200 topluluk fiyatı $0.50 gerçek dışıydı).
Spot/topluluk fiyatı ayrı satırda gösterilir.

## 3. Para birimi ve dil değiştirilebilir

- Üst çubukta **USD ⇄ TRY** ve **TR ⇄ EN** seçicileri
- `?currency=TRY`, `?lang=en` query parametreleri (paylaşılabilir)
- TRY seçilince fiyatlar kurdan çevrilir, kur tarihi görünür, `lang` özniteliği güncellenir
- Filtreler korunur (tercih değiştirirken arama/sağlayıcı kaybolmaz)
- JS kapalıysa `<noscript>` Uygula düğmesi

## 4. Token sayacı eklendi — `/token-sayaci`

- Kullanıcı metni yapıştırır → token, kelime, karakter sayısı
- Model seçilir → o token sayısının **girdi veya çıktı** maliyeti (USD + ₺)
- **Metin tarayıcıda kalır**, sunucuya gönderilmez
- Tahmin formülü açıkça yazılı: `token ≈ karakter/4 + Türkçe×0,35 + noktalama×0,15`
- Test: 249 karakter → 75 token, Anthropic Fable-5 girdi $0.00075

## 5. Doğrulama işaretleri kaldırıldı

Tablodaki yeşil "Doğrulandı" rozetleri kaldırıldı. Yerine sade **tarih** geldi;
45 günden eski kayıtlarda küçük "güncelliği geçmiş" notu kalıyor (bilgi kaybı yok, görsel gürültü yok).

## 6. Fiyat botu — AI kullanmıyor

`scripts/bot.py`: topla → QA → eşikli onay → log. Tamamen deterministik.

```json
{"tokens": {"parsed": 1557, "new": 7, "failed": []},
 "qa": {"passed": 7, "failed": 0},
 "approval": {"approved": 7, "held_for_review": 0},
 "gpu": {"quotes": 157, "new": 4, "failed": []}}
```

- **%50 üzeri fiyat değişimini otomatik onaylamaz** — insan incelemesine bırakır
- Windows Görev Zamanlayıcı kurulu: **TokenMaliyet-Fiyat-Botu**, günde 2 kez (06:10, 18:10)
- Durum: `data/bot_state.json`, geçmiş: `data/bot_runs.jsonl`

## 7. Marka yenilendi

- **Yeni ad: TokenMaliyet** (SEO dostu, Türkçe, ürünü anlatıyor — "token maliyeti" aramasıyla örtüşüyor)
- Alt başlık: "AI API fiyat ve maliyet verisi"
- **Yeni logo:** yükselen çubuk grafik (maliyet/veri çağrışımı), indigo gradyan, 4 kademeli
  opaklık — küçük boyutta da okunur, harf içermez
- **"V0.1" etiketi kaldırıldı**

## 8. Deploy hazırlığı

| Bileşen | Durum |
|---|---|
| `Dockerfile` (non-root, healthcheck) | hazır |
| `docker-compose.yml` (db + web + bot) | hazır |
| Güvenlik başlıkları (CSP, HSTS, nosniff…) | hazır |
| Gzip + statik önbellek | hazır |
| `/health/full` (DB + veri tazeliği) | hazır |
| `.env.production.example` | hazır |
| `docs/DEPLOY.md` (kontrol listesi + rollback) | hazır |
| Testler | **68 geçiyor** |

## Test ve doğrulama

```
68 passed, 1 warning in 1.72s
```

Tüm rotalar 200: `/fiyatlar` `/hesaplayici` `/karsilastir` `/token-sayaci` `/gpu-maliyetleri`
`/rehber` `/hakkinda` `/modeller/...` `/sitemap.xml` `/robots.txt` `/health/full` `/api/v1/model-options`

## Sizden gereken 3 şey (canlıya çıkmadan)

1. **Alan adı** → `.env` içindeki `SITE_URL`
2. **ADMIN_TOKEN** → şu an `YerelAdmin2026-degistir`, mutlaka değiştirin
3. **POSTGRES_PASSWORD** → güçlü ve benzersiz

## Dürüst notlar

- GPU fiyatlarında tek bir aykırı değer (H200 topluluk $0.50) tabloyu bozuyordu; on-demand
  varsayılanı + aykırı değer filtresiyle çözüldü. Bu bir **veri kalitesi kararı**, kozmetik değil.
- Token sayacı **tahmin**dir; gerçek tokenizer %15–40 farklı olabilir. Sayfada bu açıkça yazıyor.
- İngilizce çeviri gezinme/etiketlerle sınırlı; rehber yazıları Türkçe.
- Ödeme altyapısı yok, Lighthouse ölçülmedi, `og:image` yok — V0.2.
