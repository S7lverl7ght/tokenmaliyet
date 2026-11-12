# Fiyat Uyarisi Formu — Canli ve Ucretsiz (12.11.2026)

## Mimari

```
Kullanici formu doldurur
  -> POST /api/uyari  (Cloudflare Pages Function)
  -> Cloudflare D1 (SQLite) kayit
  -> (opsiyonel) Resend ile onay e-postasi
```

Statik sitede sunucu yok; bu yuzden form Cloudflare Pages Functions + D1 ile calisir.

## Maliyet: 0 TL

| Servis | Ucretsiz limit | Kullanilan |
|---|---|---|
| Pages Functions | 100.000 istek/gun | ~10-50 |
| Cloudflare D1 okuma | 5M satir/gun | ~100 |
| Cloudflare D1 yazma | 100.000 satir/gun | ~10 |
| D1 depolama | 5 GB | <1 MB |
| Resend e-posta | 100/gun, 3.000/ay | opsiyonel |

Kaynak: [D1 pricing](https://developers.cloudflare.com/d1/platform/pricing/),
[Resend limits](https://resend.com/docs/knowledge-base/account-quotas-and-limits)

## Bilesenler

| Dosya | Gorev |
|---|---|
| `functions/api/uyari.js` | POST isleyici: dogrulama + D1 yazma |
| `db/alerts.sql` | D1 semasi (`price_alerts` tablosu) |
| `wrangler.toml` | D1 binding tanimi |
| `backend/app/web/templates/uyari.html` | Form + JS gonderim |
| `tests_nodb/test_alert_function.py` | 7 sozlesme testi |

## D1 veritabani

- Ad: `tokenmaliyet-alerts`
- ID: `d5ef2d86-f3d5-460f-92ee-3c08da43958e`
- Bolge: EEUR
- Binding: `DB` (Pages production)

## Dogrulama (canli)

```
gecerli kayit     -> 200 {"ok":true,...}
gecersiz e-posta  -> 400 "Gecerli bir e-posta adresi girin."
onay yok          -> 400 "Aydinlatma metnini onaylamaniz gerekir."
D1 kaydi          -> id=2, target=deepseek|deepseek-v4-pro|, confirmed=0
```

## E-posta gondermek icin (opsiyonel)

1. [resend.com](https://resend.com) ucretsiz hesap acin
2. API key alin
3. `tokenmaliyet.com` alan adini Resend'de dogrulayin (DNS kayitlari)
4. Cloudflare Pages -> Settings -> Environment variables:
   - `RESEND_API_KEY` = `re_...`
   - `ALERT_FROM` = `uyari@tokenmaliyet.com`
   - `SITE_URL` = `https://tokenmaliyet.com`

Bu degiskenler tanimli olmasa bile **kayit alinir**; sadece onay e-postasi gitmez.

## Bilinen sinirlar

- **Cift onay tamamlanmadi**: `confirm_token` uretiliyor ama onay sayfasi yok.
  Kullanici kaydolur, e-posta gelmez (RESEND tanimli degilse).
- **Iptal linki calismiyor**: `/uyari?iptal=<token>` sayfasi henuz yok.
- **Fiyat degisince otomatik bildirim yok**: `refresh.yml` her gun calisiyor ama
  uyari e-postasi gonderen adim yok. Eklenmesi icin Resend + karsilastirma mantigi gerekir.

Bu uc madde bilincli olarak birakildi: e-posta gonderimi icin Resend hesabi ve
alan adi dogrulamasi gerekiyor, bunlar sizin hesabinizda yapilmali.

## Hata yapilan ve duzeltilen

1. `conftest.py` testleri DB yoksa `OperationalError` ile patliyordu -> `pytest.skip`.
2. Dosya testleri DB'ye bagimliydi -> `tests_nodb/` ayri dizine tasindi.
3. `refresh.yml` YAML girintisi bozuldu (`TEST_DATABASE_URL` 2 bosluk eksik) ->
   workflow 422 verdi, duzeltildi.
4. Yerel `.env`'de iptal edilmis CF token'i wrangler'i bozuyordu -> temizlendi.
