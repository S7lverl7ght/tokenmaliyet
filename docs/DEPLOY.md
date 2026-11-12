# TokenMaliyet — Deploy Hazirlik Kontrol Listesi

Sunucuya cikmadan once tamamlanmasi gerekenler. **Durum: kod tarafi hazir**,
asagidaki 3 madde sizin kararinizi bekliyor.

## 1. Kod tarafi (tamamlandi)

| Madde | Durum | Kanit |
|---|---|---|
| Docker imaji + compose | EVET | `Dockerfile`, `docker-compose.yml` (db + web + bot) |
| Saglik kontrolu | EVET | Docker `HEALTHCHECK`, `/health`, `/health/db`, `/health/full` |
| Guvenlik basliklari | EVET | CSP, nosniff, X-Frame-Options, Referrer-Policy, HSTS (prod) |
| Gzip | EVET | `GZipMiddleware` (800 bayt ustu) |
| Statik onbellek | EVET | `max-age=31536000, immutable` + surumlu URL |
| API onbellek | EVET | `max-age=60` |
| Ortam degiskenleri | EVET | `.env.production.example` — sirlar repoda degil |
| Sema gocu | EVET | `alembic upgrade head` (bos DBde dogrulandi) |
| Yedek/geri yukleme | EVET | `scripts/backup_db.ps1`, `restore_db.ps1` (test edildi) |
| Testler | EVET | **68 test** geciyor |
| SEO | EVET | sitemap (500+ URL), robots, canonical, noindex kurallari, JSON-LD |
| Erisilebilirlik | EVET | 0 kontrast ihlali, etiketli formlar, tek H1 |
| Mobil | EVET | 375 pxde tasma yok, kart gorunumu |
| Bot | EVET | `scripts/bot.py`, gunluk 06:10 ve 18:10 gorevi kurulu |

## 2. Sizin doldurmaniz gerekenler

| # | Ne | Nerede | Not |
|---|---|---|---|
| 1 | **Alan adi** | `.env` -> `SITE_URL` | Canonical/OG/sitemap bu degeri kullanir |
| 2 | **ADMIN_TOKEN** | `.env` | `python -c "import secrets;print(secrets.token_urlsafe(32))"` |
| 3 | **POSTGRES_PASSWORD** | `.env` | Guclu ve benzersiz olmali |
| 4 | Hosting | — | Asagidaki seceneklerden biri |

**Su anki `ADMIN_TOKEN` degeri gelistirme amacli** (`YerelAdmin2026-degistir`) — canliya
cikmadan mutlaka degistirin. Degistirilmezse yonetim paneli tahmin edilebilir anahtarla acik kalir.

## 3. Hosting secenekleri

### A) Tek VPS (en basit, ~5–10 $/ay)

```bash
git clone <repo> /opt/tokenmaliyet && cd /opt/tokenmaliyet
cp .env.production.example .env   # degerleri doldurun
docker compose up -d
docker compose exec web alembic upgrade head
docker compose exec web python -m app.seed
```

Ardindan Caddy/nginx + Let Encrypt ile 443e TLS.

### B) Yonetilen (Railway / Render / Fly.io)

- Web servisi: `Dockerfile`
- PostgreSQL eklentisi: saglayicinin yonetilen DBsi
- Bot: ayri worker servisi (`python scripts/bot.py` + cron/interval)

### C) Cloudflare onunde

Sayfalar sunucu-render; Cloudflarei onbellek + TLS katmani olarak kullanin
(`/api/*` ve `/admin/*` onbellek disi birakilmali).

## 4. Cikis sonrasi ilk 30 dakika

```bash
curl -s https://<alanadi>/health/full | jq        # status ok, data_age_hours < 48
curl -s https://<alanadi>/robots.txt              # Sitemap satiri dogru alan adini gostermeli
curl -s https://<alanadi>/sitemap.xml | head -5
curl -sI https://<alanadi>/fiyatlar | grep -i "content-security\|strict-transport"
```

- Google Search Consolea sitemap gonderin.
- `/admin/kuyruk` girisini deneyin; `ADMIN_TOKEN` calismiyorsa panel 403 doner (dogru davranis).
- Bot gorevini bir kez elle calistirip `data/bot_runs.jsonl` ciktisini kontrol edin.

## 5. Bilinen eksikler

1. **Kullanici testi** yapilmadi (kilavuz 5–8 kisi istiyor).
2. **Lighthouse** olculmedi; JS kritik yolda degil, LCPnin hedefte olmasi beklenir.
3. **Odeme/uyelik yok** — V0.2 kapsami.
4. **og:image** uretilmedi; paylasim gorseli sablonu eklenebilir.
5. **Veri saglayici sozlesmesi**: fiyat sayfalari her zaman ayni yapida kalmiyor; bot
   basarisiz toplamada `partial` doner ve eski fiyati guncel gibi gostermez. Haftalik kontrol onerilir.

## 6. Geri alma (rollback)

```bash
docker compose down
docker compose up -d --build <onceki-imaj-etiketi>
./scripts/restore_db.ps1 -Dump data/backup/<dosya>.dump
```
