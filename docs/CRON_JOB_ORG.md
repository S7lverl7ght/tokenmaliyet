# Dış Tetikleyici — cron-job.org (GÜNCELLENDİ 19.11.2026)

## Durum: 422 hatası alıyorsunuz

cron-job.org panelinde her çalışma şunu gösteriyor:

```
Başarısız (HTTP hatası) 422 Unprocessable Entity
```

## Kesin neden (test edildi)

GitHub `workflow/dispatches` ucu, gövde yoksa veya yanlışsa **422** döner.
Dört senaryo test edildi:

| Gönderilen gövde | Sonuç |
|---|---|
| (gövde yok) | `422 — nil is not an object` |
| `{}` | `422 — "ref" wasn't supplied` |
| `{"ref":"master"}` | `422 — No ref found for: master` |
| **`{"ref":"main"}`** | **204 OK** |

Yani panelde **gövde (body) alanı boş** kalmış veya `master` yazılmış.

## Doğru yapılandırma

| Alan | Değer |
|---|---|
| URL | `https://api.github.com/repos/S7lverl7ght/tokenmaliyet/actions/workflows/refresh.yml/dispatches` |
| Yöntem | `POST` |
| **Gövde (Body)** | `{"ref":"main"}` |
| İçerik türü | `application/json` |
| Başlık | `Authorization: Bearer <PAT>` |
| Başlık | `Accept: application/vnd.github+json` |
| Başlık | `User-Agent: cron-job-org` (zorunlu — GitHub UA'sız isteği reddeder) |

**Kritik:** `Authorization` başlığında `Bearer ` öneki (boşluk dahil) olmalı.

## 422 alıyorsanız sırayla kontrol edin

1. **Gövde boş mu?** → `{"ref":"main"}` yazın.
2. **`master` mı yazıyor?** → dal adı `main`.
3. **Content-Type** `application/json` mı?
4. **User-Agent** başlığı var mı? (yoksa GitHub 403 verir)
5. **PAT süresi dolmuş mu?** → 401 alırsınız, 422 değil.

## Artık şart mı?

**Hayır, ama faydalı.** 19.11.2026'da `refresh.yml` zamanlaması
**6 saatte bir → 2 saatte bir** yapıldı. Ölçüm: GitHub'ın kendi cron'u
8+ saat gecikiyordu (03:10Z yerine 11:30Z). 2 saatte bir denemede gün içinde
birkaç çalışma mutlaka düşer.

Yine de dış tetikleyici **belirleyici zamanlama** sağlar (ör. her sabah 06:00'da
kesin çalışsın istiyorsanız). Kurulu kalabilir; bozukken zararı yok, çünkü
GitHub cron'u zaten çalışıyor.

## Kontrol komutu

```powershell
curl.exe -sS -o NUL -w "%{http_code}\n" -X POST \
  "https://api.github.com/repos/S7lverl7ght/tokenmaliyet/actions/workflows/refresh.yml/dispatches" \
  -H "Authorization: Bearer $env:GITHUB_PAT" \
  -H "Accept: application/vnd.github+json" \
  -H "User-Agent: cron-job-org" \
  -H "Content-Type: application/json" \
  -d '{"ref":"main"}'
```

Beklenen: `204`. 422 alırsanız gövde/Content-Type hatalı.
