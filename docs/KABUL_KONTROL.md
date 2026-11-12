# V0.1 Kabul Kontrol Listesi — Doğrulama Sonuçları

Kontroller 11.11.2026 tarihinde bu makinede fiilen çalıştırılarak doldurulmuştur.

| # | Madde | Durum | Kanıt |
|---|---|---|---|
| 1 | DSH sürüm/profil bilgisi kaydedildi, mevcut kurulum korundu | ✅ | DSH web profili (port 62970) çalışıyor; profil/credential değiştirilmedi |
| 2 | Python 3.12 sanal ortamı yeniden kurulabilir | ✅ | `.venv` + `requirements.txt` |
| 3 | PostgreSQL 18.x localhost'tan bağlanıyor | ✅ | 18.6, 127.0.0.1:5432, `/health/db` → ok |
| 4 | Beş provider ve resmî kaynak kayıtları mevcut | ✅ | `app.seed` → 5 provider, 5 data_source |
| 5 | OpenRouter collector ham snapshot üretiyor | ✅ | `data/raw/openrouter_models_*.txt`, 1.386 satır |
| 6 | Diğer dört provider için adapter tamamlandı | ✅ | deepseek 12, gemini 93, anthropic 60, openai 12 |
| 7 | Her gözlemde source, observed_at, currency, billing_unit, dimension | ✅ | şema + QA `required_fields` |
| 8 | Onaylanmamış fiyat `/api/v1/prices` içinde görünmüyor | ✅ | `test_only_approved_prices_are_published` |
| 9 | Eski fiyat gözlemleri değiştirilmiyor/silinmiyor | ✅ | `test_new_observation_stored_when_price_changes` |
| 10 | Health ve DB health geçiyor | ✅ | `/`, `/health`, `/health/db` → 200 |
| 11 | Test paketi başarılı | ✅ | `7 passed` |
| 12 | `.env` ve credential Git dışında | ✅ | `.gitignore` |
| 13 | Yedek geri yükleme provası yapıldı | ✅ | `scripts/backup_db.ps1` + `restore_db.ps1` |
| 14 | Şema değişiklikleri Alembic üzerinden | ✅ | `migrations/versions/cef684d01b8d`, boş DB'de doğrulandı |
| 15 | Idempotency: aynı veri ikinci kez yazılmıyor | ✅ | 2. çalıştırma: `new_pending=0` |
| 16 | Fiyat değişiminde otomatik onay koruması | ✅ | `approve.py --max-change-pct` eşiği aşan satırı bekletir |

## Bilinen eksikler (V0.2)

- Admin onay arayüzü yok; onay CLI ile yapılıyor (planlanan tasarım).
- Üyelik/ödeme, Next.js arayüzü, fiyat değişikliği uyarıları V0.2 kapsamında.
- Bazı Gemini satırlarında ürün adı ≠ API kimliği (ör. `gemini-*-image`); rapor bu satırları medya
  modeli olarak ayırır ve tasarruf tablosuna almaz.
