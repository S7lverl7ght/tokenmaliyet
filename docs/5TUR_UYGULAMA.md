# 5. Tur Denetim Raporu — Uygulama Durumu

Kaynak: `KAPSAMLI_DENETIM_VE_GELISTIRME_RAPORU.md` (13.11.2026)
Uygulama: 13.11.2026 · **197 test geçiyor** · commit `d596dc5`

---

## Kapatılan P0 bulgular (4/4)

### P0-1 · Stored XSS ✅

Rapor haklıydı. `target_label` alanı HTML'e kaçışsız basılıyordu.

**Çözüm:** `functions/_lib/sanitize.js` — `escapeHtml()` + `headerSafe()`.
Uygulandığı yerler: `onayla.js`, `iptal.js`, `uyari.js`, `bildir.js`.

**Canlı kanıt:**
```
payload: <img src=x onerror=alert(1)>
onay sayfası çıktısı: &lt;img src=x onerror=alert(1)&gt;
ham script: YOK
```

Ek olarak e-posta başlığı enjeksiyonuna (CRLF) karşı `headerSafe()` eklendi.

### P0-2 · Token sayacı bozuk ✅

**Kök neden:** `export_static.py` `dist/api/v1/model-options` içine 89 baytlık
hata mesajı yazıyordu; token sayacı `list.forEach()` çağırınca `TypeError` alıyordu.

**Çözüm:** Artık gerçek JSON yazılıyor + `Array.isArray()` koruması.

**Canlı kanıt:**
```
/api/v1/model-options -> 200, 89.203 bayt, 487 model, cache_price dahil
```

### P0-3 · İstemci hesap motoru ✅

Raporun en kritik bulgusu. Statik sitede form gönderilince sayfa yenileniyor
ama sonuç kartları derleme anındaki değerlerde kalıyordu.

**Çözüm:** `calculator.html` ve `compare.html` içine saf JS hesap motoru:
- `recalcClient()` — model, token, dil, önbellek değişince anında günceller
- Formül `backend/app/web/calc.py` ile **birebir aynı**
- Önbellek karışımı ve Türkçe çarpanı dahil

**Doğrulama (JS vs Python, 4 senaryo):**
```
senaryo                     JS         Python
tr, cache 0              1545.7500   1545.7500
en, cache 0               675.0000    675.0000
tr, cache 50%            1236.6000   1236.6000
en, cache 50%, 10M/2M      46.5000     46.5000
```
Birebir aynı.

### P0-4 · MIME çakışması ✅

`/api/*` için global `application/json` zorlanıyordu; onay/iptal HTML dönüyordu.

**Çözüm:** Uç bazında MIME tanımı.

**Canlı kanıt:**
```
/api/onayla  -> text/html; charset=utf-8   (HTML sayfa)
/api/v1/*    -> application/json; charset=utf-8
```

---

## Kapatılan P1 bulgular (2/2)

### P1-1 · 50 subrequest sınırı ✅

`bildir.js` her aboneye ayrı `fetch` yapıyordu; 50 aboneden sonra fonksiyon
öldürülüyordu.

**Çözüm:** Resend `/emails/batch` ucu — tek istekte 100 e-posta, 100'lük parçalar.
`sendMailBatch()` eklendi.

### P1-2 · PAT 30 gün riski ⚠️ DOKÜMANTE EDİLDİ

Kod tarafında çözümü yok; kullanıcının yeni token alması gerekir.
`docs/CRON_JOB_ORG.md` içine yenileme talimatı yazıldı.

---

## Kapatılmayanlar (bilinçli)

| Bulgu | Neden |
|---|---|
| Turnstile / rate limit (P0-5) | Cloudflare hesabında site key + secret key oluşturulmalı; kullanıcı işlemi |
| Kalıcı bulut DB (P1-3) | Neon/Supabase hesabı gerekiyor; ayrıca GitHub Actions'ta fiyat geçmişi tutmak için tasarım kararı |
| Anlık tablo filtresi (P1-4) | Ayrı iş; rapor P1'e koymuş |
| GPU affiliate (P1-5) | Affiliate başvurusu kullanıcıda |
| Faz 2/3 gelir kalemleri | Kullanıcı onayı + ticari karar |

---

## Doğrulama özeti

```
197 passed, 6 skipped
Canlı: model-options 89 KB JSON (487 model)
Canlı: XSS payload kaçışlı
Canlı: MIME tipleri doğru
JS == Python (4 senaryo, birebir)
Deploy: 7b7d8e8a.tokenmaliyet.pages.dev -> tokenmaliyet.com
```

## Testler

`tests_nodb/test_audit_round5.py` — 12 yeni test:
- `test_escape_helper_exists`, `test_confirm_page_escapes_label`
- `test_unsubscribe_page_escapes_label`, `test_email_html_escapes_user_input`
- `test_export_writes_real_model_options`, `test_token_counter_guards_non_array`
- `test_calculator_has_client_engine`, `test_compare_has_client_engine`
- `test_options_include_cache_price`, `test_headers_have_per_endpoint_mime`
- `test_batch_mail_used`
