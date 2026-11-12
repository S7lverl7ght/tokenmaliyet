# GitHub + CI/CD Kurulumu (12.11.2026)

## Canli
- **Site:** https://tokenmaliyet.com (Cloudflare Pages)
- **Repo:** https://github.com/S7lverl7ght/tokenmaliyet (public)
- **CI durumu:** basarili
- **Veri yenileme:** basarili, gunde 2 kez (06:10 / 18:10 TR)

## Workflow'lar

| Workflow | Tetikleyici | Ne yapar |
|---|---|---|
| `ci.yml` | push, PR, elle | Testler (142) + pip-audit |
| `refresh.yml` | cron 03:10+15:10 UTC, push, elle | Sema -> topla -> kur -> golden -> statik -> test -> commit -> deploy |

## Cozulen 5 gercek hata

1. **`__init__.py` gitignore'a takiliyordu** — `_*.py` kurali `__init__.py`'i de
   yutuyordu. CI'da `ImportError: cannot import name '__version__'` veriyordu.
   Cozum: `.gitignore`'a `!**/__init__.py` istisnasi + `git add -f`.
2. **Sema olusturma alembic ile yapiliyordu** — CI ortaminda migration
   uygulanmiyordu. Cozum: `scripts/init_dev_db.py` (create_all).
3. **Golden test 'EKSIK' ile 'DEGISTI'yi ayirmiyordu** — API anahtari olmayan
   saglayici (OpenAI) yuzunden her calisma kiriliyordu. Cozum: DEGISTI = hata,
   EKSIK = uyari.
4. **Testler uretim semasini siliyordu** — `conftest.py` `drop_all` yapiyor;
   ayni DB'de kosunca statik uretim tablosuz kaliyordu. Cozum: testler ayri
   `ai_maliyet_test` veritabaninda + statik uretim testlerden ONCE.
5. **Kur (fx) yokken sayfa cokuyordu** — `gpu.html`, `prices.html`, `model.html`
   `fx_rate`'i dogrudan carpiyordu (`float * None`). Cozum: `{% if fx_rate %}`
   korumasi + CI'a TCMB kur adimi.

## Secrets (GitHub)
- `ADMIN_TOKEN` — 64 karakter rastgele
- `CLOUDFLARE_ACCOUNT_ID` — 279485e31b16d58ec7d5603dead31b90
- `CLOUDFLARE_API_TOKEN` — bos (Pages deploy icin wrangler OAuth kullaniliyor)

## Onemli not: git push

Windows'ta `git-credential-helper-selector` askida kaliyor ve push sonsuza kadar
bekliyor. Cozum: credential helper'i devre disi birak:

```powershell
$env:GIT_CONFIG_COUNT=2
$env:GIT_CONFIG_KEY_0='credential.helper'; $env:GIT_CONFIG_VALUE_0=''
$env:GIT_CONFIG_KEY_1='credential.interactive'; $env:GIT_CONFIG_VALUE_1='false'
git push https://KULLANICI:TOKEN@github.com/KULLANICI/tokenmaliyet.git main
```

## Guvenlik temizligi

Push oncesi 4 dosyada sabit DB sifresi vardi, kaldirildi:
`scripts/backup_db.ps1`, `scripts/restore_db.ps1`, `scripts/health_and_backup.ps1`,
`tests/conftest.py`. Hepsi artik `PGPASSWORD` ortam degiskeni bekliyor.

## Elle tetikleme

```powershell
# Actions sekmesi -> workflow -> Run workflow
# veya API:
curl -X POST -H "Authorization: token $env:GH_TOKEN" \
  https://api.github.com/repos/S7lverl7ght/tokenmaliyet/actions/workflows/refresh.yml/dispatches \
  -d '{"ref":"main"}'
```
