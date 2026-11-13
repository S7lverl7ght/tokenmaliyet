# Turnstile Entegrasyonu (13.11.2026)

## Widget

| Alan | Değer |
|---|---|
| Ad | tokenmaliyet.com (Spin) |
| Site key | `0x4AAAAAAF_TxkQHNciYw5a6` (public) |
| Secret key | Cloudflare Pages secret olarak saklı (`TURNSTILE_SECRET`) |
| Mod | Managed (görünmez → riskli trafikte etkileşimli) |
| Hostname | `tokenmaliyet.com`, `localhost`, `127.0.0.1` |
| CSP | script/connect/frame-src `challenges.cloudflare.com` izinli |

## Akış

```
Kullanıcı formu doldurur
  -> Turnstile widget token üretir (cf-turnstile-response)
  -> POST /api/uyari
  -> verifyTurnstile() -> challenges.cloudflare.com/turnstile/v0/siteverify
  -> başarılıysa D1'e yaz + onay e-postası
  -> başarısızsa 400 (kayıt YOK, e-posta YOK)
```

## Dosyalar

| Dosya | Görev |
|---|---|
| `functions/_lib/turnstile.js` | `verifyTurnstile()` + `siteKey()` |
| `functions/api/uyari.js` | Siteverify çağrısı, DB yazımından ÖNCE |
| `backend/app/web/templates/uyari.html` | Widget div + api.js |
| `backend/app/web/render.py` | `turnstile_site_key` context |
| `scripts/export_static.py` | CSP: challenges.cloudflare.com |

## Güvenlik kararları

1. **Fail-closed:** `TURNSTILE_SECRET` tanımlı değilse istek **reddedilir**
   (`not_configured`), sessizce geçirilmez.
2. **Secret istemciye gitmez:** Test ile doğrulandı — canlı HTML'de secret yok.
3. **Site key hardcode değil:** `TURNSTILE_SITE_KEY` env veya varsayılan.
4. **Token tek kullanımlık:** Cloudflare siteverify her token'ı bir kez kabul eder.
5. **IP iletimi:** `cf-connecting-ip` başlığı siteverify'e `remoteip` olarak gider.

## Canlı doğrulama

```
POST /api/uyari (token yok)
  -> 400 {"ok":false, "turnstile":"missing_token"}

POST /api/uyari (sahte token 'XXXX.DUMMY.TOKEN.XXXX')
  -> 400 {"ok":false, "turnstile":"rejected"}

GET /uyari/
  -> data-sitekey 0x4AAAAAAF_TxkQHNciYw5a6
  -> cf-turnstile div var
  -> api.js yüklü
  -> secret sızması YOK

CSP: script-src/connect-src/frame-src challenges.cloudflare.com
```

## Testler

`tests_nodb/test_turnstile.py` — 6 test:
- `test_verify_helper_exists`
- `test_secret_never_in_client`
- `test_form_has_widget_and_script`
- `test_site_key_in_context_with_correct_default`
- `test_api_verifies_before_writing` (siteverify DB'den önce)
- `test_csp_allows_challenges`

Toplam suite: **211 passed**.

## Kalan iş

Gerçek tarayıcıda uçtan uca test (widget çözülüp kayıt oluşması) yapılmadı;
tarayıcı otomasyonu bu oturumda Turnstile iframe'ini geçemedi. API katmanı
hem reddi hem de siteverify çağrısını doğruluyor.

**Kullanıcı kontrolü:** `/uyari` sayfasını açıp widget'ın göründüğünü ve
gerçek bir e-posta ile kaydın oluştuğunu doğrulamak yeterli.
