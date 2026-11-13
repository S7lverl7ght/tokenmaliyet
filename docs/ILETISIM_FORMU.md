# İletişim Formu (13.11.2026)

## Sorun

`iletisim@tokenmaliyet.com` adresi sitede yazıyordu ama **böyle bir mailbox yok**.
Kullanıcı yazsa da kimse görmezdi.

## Çözüm: yerleşik iletişim formu

`/iletisim` sayfası artık gerçek bir form. Kullanıcı mesajı sitede yazar;
sistem hem **kaydeder** hem de **e-posta ile iletir**.

```
Kullanıcı formu doldurur
  -> Turnstile bot kontrolü (fail-closed)
  -> alan doğrulama (ad, e-posta, konu, mesaj >= 10 karakter)
  -> D1'e YAZ  <-- önce bu (mail düşse bile mesaj kaybolmaz)
  -> Resend ile omerktn55@gmail.com'a gönder
     Reply-To = kullanıcının kendi adresi
```

## Neden bu yöntem (önerdiğim ve uyguladığım)

| Seçenek | Değerlendirme |
|---|---|
| `mailto:` bağlantısı | Kullanıcının mail istemcisi gerekir; mobilde çoğu kişi terk eder. **Seçilmedi.** |
| Formu 3. parti servise (Formspree) bağlamak | Ek bağımlılık, ücretsiz kota, veri ABD'de. **Seçilmedi.** |
| **Cloudflare Function + D1 + Resend** | Zaten kurulu altyapı, ek maliyet 0, mesaj kaybolmaz. **Seçildi.** |

**Kritik tasarım kararı:** önce D1'e yaz, sonra mail at. Resend kotası dolarsa
veya servis düşerse mesaj yine elimizde kalır. `mail_sent` / `mail_error`
alanları teşhis için tutulur.

## Neden ayrı mailbox gerekmiyor

Resend'de **doğrulanmış olan gönderen adresidir** (`uyari@tokenmaliyet.com`).
Alıcı olmak için domain doğrulaması gerekmez — `omerktn55@gmail.com`'a
sorunsuz gönderilir. Yani yeni bir mailbox açmaya gerek yok.

## Kullanıcıya güvenlik

- **Reply-To** kullanıcının adresi → Gmail'de "Yanıtla" doğrudan kullanıcıya gider
- **Bal küpü** (`website` alanı, görünmez) → botlar doldurur, sessizce yutulur
- **Turnstile** → Managed mod, çerez yok
- **IP başına 24 saatte 5 mesaj** sınırı
- **IP tuzlanarak** saklanır (SHA-256 ilk 8 bayt) — KVKK dostu

## Dosyalar

| Dosya | Görev |
|---|---|
| `functions/api/iletisim.js` | Form ucu: doğrula → D1 → mail |
| `db/contact.sql` | `contact_messages` tablosu + indeksler |
| `backend/app/web/templates/iletisim.html` | Form + JS (sayfa yenilenmez) |
| `backend/app/web/routes.py` | `GET/POST /iletisim` (JS kapalı yedeği) |
| `functions/_lib/mail.js` | `replyTo` desteği eklendi |

## Yan bulunan hata (düzeltildi)

Formun üstünde **boş bir uyarı kutusu** görünüyordu. Sebep:
```css
.notice { display: flex; }   /* [hidden] niteliğini eziyordu */
```
`[hidden]{display:none !important}` eklendi. Bu hata **tüm sitede** vardı
(uyarı panelleri, gizli bölümler); tek kuralla düzeldi.

## Canlı doğrulama (gerçek tarayıcı)

```
Form dolduruldu -> Mesajı gönder
Sonuç: "Mesajınız iletildi." (notice-ok)
D1 kaydı: id=1, name="Test Kullanici", mail_sent=1, mail_error=null
```

Test kaydı sonra silindi.

## Testler

`tests_nodb/test_contact_form.py` — 8 test:
- form alanları, kullanıcı e-postası zorunlu
- Turnstile + bal küpü var
- `iletisim@tokenmaliyet.com` kod tabanında **yok**
- mail `omerktn55@gmail.com`'a, `replyTo: email`
- D1 yazımı mailden **önce**

Toplam: **234 passed**.

## Notlar

- Mesajlar `npx wrangler d1 execute tokenmaliyet-alerts --remote --command="SELECT * FROM contact_messages"` ile görülebilir.
- Gelen kutusu değiştirmek için Pages env: `CONTACT_INBOX`.
