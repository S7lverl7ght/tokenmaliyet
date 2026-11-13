# Dış Tetikleyici Kurulumu — cron-job.org (13.11.2026)

## Neden gerekli

GitHub Actions'ın `schedule` (cron) tetikleyicisi **garantili değil**.
Ölçüm: 12.11.2026 22:50'de 10 dakikalık test cron'u kuruldu, **9+ saat**
boyunca hiç tetiklenmedi (0 çalışma). GitHub resmî dokümanı:

> "The schedule event can be delayed during periods of high loads...
> some queued jobs may be dropped."

## Çözüm: cron-job.org (ücretsiz)

### Kurulan iş

| Alan | Değer |
|---|---|
| Başlık | TokenMaliyet veri yenileme |
| URL | `https://api.github.com/repos/S7lverl7ght/tokenmaliyet/actions/workflows/refresh.yml/dispatches` |
| Yöntem | **POST** |
| Gövde | `{"ref":"main"}` |
| Zamanlama | `0 */6 * * *` (6 saatte bir) |
| Saat dilimi | Europe/Istanbul |
| Durum | Aktif (yeşil) |

### Header'lar

```
Authorization: Bearer <GITHUB_PAT>
Content-Type: application/json
```

### Doğrulama (uçtan uca)

Aynı isteği elle göndererek test ettim:

```
POST .../refresh.yml/dispatches
Body: {"ref":"main"}
-> 204 No Content          (GitHub kabul etti)
-> GitHub Actions: workflow_dispatch, 08:08 TR
-> 18/18 adım SUCCESS (deploy dahil)
```

## Artık 3 katmanlı yedeklilik var

| Tetikleyici | Sıklık | Bağımlılık |
|---|---|---|
| GitHub `push` | Kod gönderince | Elle |
| GitHub `schedule` | 06:10 / 18:10 TR | Garanti değil |
| **cron-job.org** | **6 saatte bir** | GitHub dışı |

Bir tanesi çalışmasa diğerleri devreye girer.

## Not: PAT süresi

Kullanılan GitHub PAT (`ghp_...`) **30 gün** geçerli (12.12.2026'ya kadar).
Süresi dolunca cron-job.org isteği 401 alır.

**Yenileme:** GitHub → Settings → Developer settings → Personal access
tokens → yeni token → cron-job.org'da ilgili işin `Authorization`
header'ını güncelleyin.

Uzun vadeli çözüm: fine-grained token ile 1 yıl geçerlilik verin.

## İzleme

- cron-job.org: https://console.cron-job.org/jobs
- GitHub Actions: https://github.com/S7lverl7ght/tokenmaliyet/actions
- Site: https://tokenmaliyet.com

## Sonuç

Site ve form **PC kapalıyken kesin çalışır**. Veri yenileme artık
**6 saatte bir, GitHub cron'undan bağımsız** olarak garanti altında.
