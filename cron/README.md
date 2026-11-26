# Cron tetikleyici

## Neden

Ölçüm (26.11.2026): GitHub'ın kendi `schedule` tetikleyicisi **2 saatlik cron'u
~10 saatte bire** düşürüyordu (ölçülen aralıklar 5,7–13,1 saat). Dış tetikleyici
cron-job.org ise 422 verdiği için hiç çalışmıyordu. Sonuç: veri günde 2 kez yerine
tek sefer güncelleniyordu.

Cloudflare Workers cron trigger'ları zamanında çalışır. Bu Worker yalnızca
GitHub API'sine `workflow_dispatch` çağrısı yapar — veri işleme GitHub'da kalır.

## Kurulum

```powershell
cd C:\AI-Maliyet-Merkezi\cron

# 1) GitHub PAT (fine-grained, "Actions: read and write")
npx wrangler secret put GH_PAT

# 2) Elle tetikleme sirri (test icin)
npx wrangler secret put CRON_SECRET

# 3) Deploy
npx wrangler deploy

# 4) Test
curl.exe -X POST "https://tokenmaliyet-cron.<hesap>.workers.dev/?token=<CRON_SECRET>"
```

## Zamanlama

`20 */6 * * *` — 6 saatte bir (00:20, 06:20, 12:20, 18:20 UTC) = günde 4 tetikleme.
Ücretsiz plan sınırı günde 5.

GitHub'ın kendi schedule'ı (2 saatte bir) yedek olarak kalır; ikisi birden
çalışsa bile işlemler idempotent olduğu için mükerrer kayıt oluşmaz.
