# Fiyat Uyarisi Sistemi — Tam ve Canli (12.11.2026)

## Durum: CALISIYOR, tamamen ucretsiz

```
Kullanici formu doldurur
  -> POST /api/uyari       kayit + onay e-postasi
  -> e-postadaki link      GET /api/onayla?t=...  (cift onay)
  -> GitHub Actions        her gun fiyat degisimi kontrolu
  -> POST /api/bildir      onayli abonelere e-posta
  -> e-postadaki link      GET /api/iptal?t=...   (tek tik iptal)
```

## Maliyet: 0 TL

| Servis | Ucretsiz limit | Kullanim |
|---|---|---|
| Resend e-posta | 100/gun, 3.000/ay | ~5/gun |
| Pages Functions | 100.000 istek/gun | ~50/gun |
| Cloudflare D1 | 5M okuma + 100K yazma/gun | ~200/gun |

## Bilesenler

| Dosya | Gorev |
|---|---|
| `functions/api/uyari.js` | Kayit + onay e-postasi |
| `functions/api/onayla.js` | Cift onay (confirmed=1) |
| `functions/api/iptal.js` | Tek tik iptal |
| `functions/api/bildir.js` | Fiyat degisimi bildirimi |
| `functions/_lib/mail.js` | Resend yardimcisi |
| `db/alerts.sql` | D1 semasi |
| `scripts/alert_changes.py` | Degisim tespiti |
| `tests_nodb/test_alert_flow.py` | 8 sozlesme testi |

## Resend

- Alan adi: `tokenmaliyet.com` — **verified**
- DNS: DKIM (`resend._domainkey`), SPF (`send`, `rsend`) — hepsi verified
- Gonderen: `TokenMaliyet <uyari@tokenmaliyet.com>`

## Pages ortam degiskenleri

| Ad | Deger |
|---|---|
| `RESEND_API_KEY` | `re_...` (secret) |
| `ALERT_FROM` | `TokenMaliyet <uyari@tokenmaliyet.com>` |
| `SITE_URL` | `https://tokenmaliyet.com` |
| `BILDIR_SECRET` | rastgele 43 karakter (secret) |

`BILDIR_SECRET` ayni zamanda GitHub Secret olarak eklendi.

## Dogrulama (canli, gercek e-posta)

```
kayit          -> 200 {ok:true, mail_sent:true, needs_confirm:true}
onay e-postasi -> Resend: delivered
onay linki     -> 200 "Kaydiniz onaylandi"
gecersiz token -> 400
iptal linki    -> 200 "Uyariniz iptal edildi"
bildirim       -> 200 {ok:true, sent:1}
bildirim e-posta -> Resend: delivered
yetkisiz bildirim -> 401
D1             -> id=1, confirmed=1
```

## CI entegrasyonu

`refresh.yml` 12 adim; yeni adim: **Fiyat degisimlerini bildir**

```yaml
python scripts/alert_changes.py --out data/alert_changes.json
# 0 degisim varsa istek atilmaz
curl -X POST https://tokenmaliyet.com/api/bildir \
  -H "x-bildir-secret: $BILDIR_SECRET" --data @data/alert_changes.json
```

## Guvenlik

- `BILDIR_SECRET` olmadan bildirim ucu **401** doner
- Onay/iptal token'lari 32 karakter rastgele (`crypto.randomUUID`)
- Token formati regex ile dogrulanir (`[a-f0-9]{16,64}`)
- Onay/iptal sayfalari `noindex`
- E-posta adresleri ucuncu taraflarla paylasilmiyor

## Testler

`tests_nodb` icinde 15 test (8'i uyari akisi). Toplam suite: **157 passed**.

## Bilinen sinirlar

- **Gunluk limit**: Resend ucretsiz 100 e-posta/gun. 100+ abone olursa yeni
  abonelere e-posta gitmez (kayit yine alinir, `mail_sent:false` doner).
- **Degisim tespiti** son 36 saatlik gozlemlere bakar (`--hours 36`).
- **Toplu gonderim yok**: her aboneye tek tek gonderilir (Resend tek tek ister).
