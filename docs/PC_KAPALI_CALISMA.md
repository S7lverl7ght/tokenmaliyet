# Site PC Kapalıyken Yayında Kalır mı? (12.11.2026)

## KISA CEVAP

**EVET.** Site tamamen Cloudflare'de çalışıyor; bu bilgisayara hiç bağlı değil.

| Katman | Nerede | PC kapalıyken |
|---|---|---|
| HTML/CSS/JS (17 sayfa + 11 varyant) | Cloudflare Pages CDN | ÇALIŞIR |
| Önbellek/sertifika/DNS | Cloudflare | ÇALIŞIR |
| Fiyat uyarı formu (D1) | Cloudflare Functions + D1 | ÇALIŞIR |
| Veri yenileme (bot) | GitHub Actions | **ŞARTA BAĞLI** (aşağıya bakın) |
| Yerel PostgreSQL + uvicorn | Bu PC | Gerekmiyor |

## KANIT (yerel sunucu kapatılarak test edildi)

```
Yerel sunucu : KAPATILDI (port 8000 kapalı)
/                 200  sunucu=cloudflare  CF-RAY=True
/hesaplayici/     200  sunucu=cloudflare  CF-RAY=True
/fiyatlar/        200  sunucu=cloudflare  CF-RAY=True
/en/fiyatlar/     200  sunucu=cloudflare  CF-RAY=True
POST /api/uyari   200  {ok:true, needs_confirm:true}   <- D1'e yazdı
```

Yani site ve form, bu bilgisayar kapalıyken de birebir aynı çalışıyor.

## VERİ YENİLEME: dikkat edilmesi gereken nokta

Fiyat güncellemesi GitHub Actions ile yapılıyor. İki tetikleyici var:

1. **push** — kod gönderdiğinizde (çalışıyor, defalarca doğrulandı)
2. **schedule (cron)** — günde 2 kez, 06:10 / 18:10 TR

### Ölçülen durum

- 12.11.2026 22:50'de 10 dakikalık test cron'u kuruldu (`*/10 * * * *`)
- 60+ dakika boyunca **hiç tetiklenmedi** (0 çalışma)
- GitHub resmî dokümanı: *"schedule event can be delayed during periods of high loads...
  some queued jobs may be dropped"* — yani garanti DEĞİL
- Yeni repolarda ilk cron gecikmesi bilinen bir davranış

**Sonuç:** cron muhtemelen çalışacak ama **garanti değil**. Bu yüzden
aşağıdaki yedek mekanizma önerilir.

## ÖNERİLEN YEDEK: dış tetikleyici (ücretsiz)

### Seçenek A — cron-job.org (en kolay, ücretsiz)

1. https://cron-job.org adresinde ücretsiz hesap açın
2. Yeni cron job: **her 6 saatte bir**
3. URL (POST):
   ```
   https://api.github.com/repos/S7lverl7ght/tokenmaliyet/actions/workflows/refresh.yml/dispatches
   ```
4. Headers:
   ```
   Authorization: Bearer <GITHUB_PAT>
   Accept: application/vnd.github+json
   Content-Type: application/json
   ```
5. Body: `{"ref":"main"}`

Bu, GitHub cron'u çalışmasa bile veriyi tazeler.

### Seçenek B — Cloudflare Cron Trigger (Workers Paid gerekir)

Ücretsiz planda yok; önerilmez (maliyet).

### Seçenek C — başka bir makinede zamanlayıcı

`scripts/install_scheduler.ps1` bir Windows görevine bağlanabilir ama
o makinenin açık olması gerekir — PC kapalı senaryosunu çözmez.

## ÖZET

| Soru | Cevap |
|---|---|
| Site PC kapalıyken açılır mı? | **Evet, kesin** |
| Form çalışır mı? | **Evet, kesin** |
| Fiyatlar kendiliğinden güncellenir mi? | GitHub cron çalışırsa evet; **garanti için dış tetikleyici gerekli** |
| Veri güncellenmezse site bozulur mu? | Hayır, son veri gösterilir (tarih görünür) |

## İzleme

- https://github.com/S7lverl7ght/tokenmaliyet/actions
- https://dash.cloudflare.com/279485e31b16d58ec7d5603dead31b90/pages/view/tokenmaliyet
