# TokenMaliyet — AI API ve GPU fiyat verisi

Kaynaklı, doğrulanmış ve tarihçesi korunmuş **AI API fiyat motoru**. Windows yerel çalışır,
PostgreSQL 18 üzerinde tutar, yalnızca QA'dan geçmiş (`approved`) fiyatları API ile sunar.

## Ne yapar

1. **Toplar** — 5 sağlayıcının resmî sayfasından/API'sinden fiyat çeker (OpenAI, Anthropic,
   Google Gemini, DeepSeek, OpenRouter). Ham HTML/JSON snapshot diske yazılır.
2. **Saklar** — her fiyat bir **gözlem** (observation) satırıdır; fiyat değişince eski satır
   silinmez, yeni satır eklenir. Kaynak URL + gözlem zamanı + para birimi + fatura birimi korunur.
3. **Doğrular** — deterministik QA: zorunlu alanlar, negatif/sıfır fiyat, para birimi, bilinen
   birim, tazelik. Sonuç `verification_logs` tablosuna yazılır.
4. **Yayınlar** — sadece insan/otomatik onaydan geçen satırlar `GET /api/v1/prices` ile sunulur.
   Onaysız veri hiçbir uç noktadan görünmez.

## Kurulum (mevcut makinede hazır)

```
PostgreSQL 18.6  → 127.0.0.1:5432   veritabanı: ai_maliyet_merkezi
Python 3.12      → .venv\Scripts\python.exe
```

Sıfırdan kurulum:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
# .env dosyasını .env.example'dan oluştur ve DATABASE_URL'i düzelt
$env:PYTHONPATH="$PWD\backend"
.\.venv\Scripts\python.exe -m alembic upgrade head   # şema (create_all yerine)
.\.venv\Scripts\python.exe -m app.seed               # 5 sağlayıcı + resmî kaynak kayıtları
```

## Günlük akış

```powershell
.\run_collect.ps1          # topla → QA → pending
.\scripts\approve.py --list          # ne onaylanacak, gözden geçir
.\scripts\approve.py --auto --actor omer --max-change-pct 50   # %50'den büyük değişimi bekletir
.\run_api.ps1              # http://127.0.0.1:8000/docs
.\test.ps1                 # 7 test
```

## API

| Uç nokta | İşlev |
|---|---|
| `GET /` `GET /health` `GET /health/db` | servis ve DB sağlığı |
| `GET /api/v1/providers` | sağlayıcı kataloğu |
| `GET /api/v1/models?provider_id=` | model kataloğu |
| `GET /api/v1/prices?model_id=&provider_id=` | **yalnızca onaylı** güncel fiyatlar |
| `GET /api/v1/prices/history/{model_id}` | onaylı fiyat geçmişi |
| `GET /api/v1/fx?quote=TRY` | tarihli USD/TRY kuru + kaynak |
| `GET /api/v1/estimate?model_id=&input_tokens=&output_tokens=&quote=TRY` | maliyet tahmini |
| `GET /health/full` | DB + veri tazeliği + kayıt sayısı (izleme için) |

Örnek:

```
GET /api/v1/estimate?model_id=463&input_tokens=100000000&output_tokens=25000000&quote=TRY
→ {"usd":115.5,"converted":{"TRY":5800.87},"fx_effective_at":"2026-11-10T03:00:00+03:00"}
```

## Yedek, geri yükleme ve zamanlanmış görev

```powershell
.\scripts\backup_db.ps1                                   # data/backup/*.dump (14 gün tutulur)
.\scripts\restore_db.ps1 -Dump .\data\backup\<dosya>.dump   # ayrı DB'ye restore + sayım provası
.\scripts\install_scheduler.ps1                            # 09:15 topla, 09:45 yedek
```

Restore provası sonucu: `approved=1528` (yedek bütünlüğü doğrulandı).

## Ticari çıktılar

| Dosya | Ne işe yarar |
|---|---|
| `reports/AI_Maliyet_Raporu_<tarih>.xlsx` | Türkiye için TRY fiyat karşılaştırma + aylık senaryo + grafik |
| `reports/savings.py` | model değiştirme tasarruf hesaplayıcı (aylık/yıllık TRY) |
| `docs/GELIR_PLANI.md` | bu veriyi paraya çevirme planı |

```powershell
.\reports\savings.py --from claude-sonnet-4.5 --to deepseek-v4-pro --input-tokens 100000000 --output-tokens 25000000
```

## Veri kuralları (kısaca)

- `observed_at` = okuma zamanı, `effective_from` = kaynağın ilan ettiği yürürlük tarihi.
- Fiyat birimi kaynaktaki hâliyle saklanır (`USD/1M_tokens`, `USD/1K_requests`, `USD/image`, `USD/second`).
- OpenRouter = **pazaryeri** kanalı; model sahibinin doğrudan fiyatıyla aynı satıra yazılmaz.
- DeepSeek peak / off-peak ayrı boyuttadır; raporda standart (off-peak) esas alınır, peak `[peak]` etiketlenir.
- Gemini "starting <tarih>" gelecek fiyatı bugünkü fiyat sayılmaz.
- Negatif fiyat reddedilir; sıfır yalnızca kaynakta "free" ibaresi varsa kabul edilir.
- `.env` ve parolalar Git dışında; PostgreSQL yalnızca localhost.

## Dizin yapısı

```
backend/app/        config, db, models, pipeline (ingest+QA), main (FastAPI), seed
backend/app/collectors/   base + 5 sağlayıcı adaptörü
scripts/            init_dev_db, collect, validate, approve, collect_fx
migrations/         Alembic (tek revizyon: initial schema)
reports/            xlsx üretici + tasarruf hesaplayıcı
tests/              7 test (idempotency, immutability, QA, API)
data/raw/           ham snapshot'lar (git dışı)
```

## Bilinen sınırlar (V0.2)

Next.js arayüzü, fiyat değişikliği uyarıları, Türkçe tokenizasyon/benchmark, üyelik/ödeme yok.
Sayfa yapısı değişen sağlayıcıda collector "partial" döner ve `collection_runs.error_summary`
alanına not düşer — sessizce yanlış fiyat yayınlamaz.

## Arayüz sayfaları

| Sayfa | İşlev |
|---|---|
| `/fiyatlar` | 498 model, filtre/sıralama/sayfalama, USD⇄TRY, TR/EN |
| `/modeller/{provider}/{slug}` | Model detayı, peak/off-peak ayrı, fiyat geçmişi |
| `/karsilastir` | 2–4 model yan yana maliyet karşılaştırma |
| `/hesaplayici` | Aylık maliyet + tasarruf yüzdesi, formül açık |
| `/token-sayaci` | Metin → token tahmini → seçili modelde maliyet (tarayıcıda) |
| `/gpu-maliyetleri` | 5 sağlayıcıdan GPU-saat fiyatları (Runpod, Vast.ai, DataCrunch, Lambda, Hyperstack) |
| `/rehber` | 3 özgün maliyet yazısı |
| `/admin/kuyruk` | Korumalı doğrulama kuyruğu (ADMIN_TOKEN) |

## Fiyat botu (AI kullanmaz)

```powershell
.\scripts\bot.ps1                 # elle çalıştır
.\scripts\install_bot_task.ps1    # günlük 06:10 + 18:10 görevi kur
```

Bot: topla → QA → **%50'den büyük değişimi onaylamadan beklet** → log yaz.
Durum: `data/bot_state.json`, geçmiş: `data/bot_runs.jsonl`.

## Deploy

```bash
docker compose up -d
docker compose exec web alembic upgrade head
```
Ayrıntı ve kontrol listesi: [docs/DEPLOY.md](docs/DEPLOY.md)
