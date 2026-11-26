# Zamanlanmış İşler — Durum ve Ölçüm (26.11.2026)

## Sorun: cron "durmuş" görünüyordu

Kullanıcı bildirdi, **doğruydu**. Sistem çalışıyor gibi görünüyordu ama veri tazeliği bozulmuştu.

## Ölçüm

| Ölçüm | Sonuç |
|---|---|
| Son çalışma | 26.11 10:46 UTC (6,5 saat önce) |
| Veri yaşı | 6,5 saat |
| Günlük çalışma sayısı | **2–3** (beklenen 12) |
| workflow_dispatch (cron-job.org) | **0 çalışma** |
| Ölçülen aralıklar | 5,7 – 13,1 saat |

## İki kök neden

### 1. GitHub kendi cron'unu kısıtlıyor

2 saatte bir istenmiş (`10 */2 * * *`), ama GitHub bunu **~10 saatte bire** düşürüyor.
GitHub resmî dokümanı bunu kabul ediyor: "yinelenen işler yük altında gecikebilir
veya düşürülebilir". Saatlik dilim sıklaştıkça daha çok düşürülüyor.

### 2. cron-job.org hiç çalışmıyor

Panelde her deneme `422 Unprocessable Entity`. Son 15 çalışmanın **hiçbiri**
`workflow_dispatch` değil — dış tetikleyici hiç başarılı olmamış.

## Çözüm: Cloudflare Workers cron

`cron/worker.js` — 6 saatte bir tetiklenir, GitHub'a `workflow_dispatch` yapar.

| | |
|---|---|
| Worker | `https://tokenmaliyet-cron.omerktn55.workers.dev` |
| Zamanlama | `20 */6 * * *` (00:20, 06:20, 12:20, 18:20 UTC) |
| Günlük tetikleme | 4 (ücretsiz plan sınırı 5) |
| Kimlik | `GH_PAT` sırrı (OAuth token, `workflow` izni var) |
| Elle tetikleme | `POST /?token=<CRON_SECRET>` |

Neden Cloudflare: GitHub'ın aksine cron trigger'ları **zamanında** çalışır.

## Doğrulama (canlı)

```
GET  /                          -> {"ok":true,"hasPat":true}
POST /?token=yanlis             -> 401
POST /?token=<dogru>            -> {"ok":true,"dispatched":true,"status":204}
GitHub'da yeni calisma          -> workflow_dispatch, completed/success
Veri zamani                     -> 10:46 -> 17:27 (tazelendi)
```

## Yedeklilik

İki mekanizma birlikte çalışır:
1. **Cloudflare Worker** — 6 saatte bir, zamanında
2. **GitHub schedule** — 2 saatte bir istenir, ~10 saatte bir gerçekleşir (yedek)

İşlemler idempotent: aynı gün birden çok kez çalışsa da mükerrer kayıt olmaz.

## Kurulum (yeniden gerekirse)

```powershell
cd C:\AI-Maliyet-Merkezi\cron
npx wrangler secret put GH_PAT      # Actions: read/write izinli PAT
npx wrangler secret put CRON_SECRET # elle tetikleme sirri
npx wrangler deploy
```

## İzleme

```powershell
curl.exe -sS "https://tokenmaliyet-cron.omerktn55.workers.dev/"
```

GitHub → Actions → "Veri yenile ve yayinla" ile çalışma geçmişi görülür.

**Not:** Worker sırrı `.cron_secret.txt` dosyasında, `.gitignore`'da. Kaybolursa
`wrangler secret put CRON_SECRET` ile yenilenir.