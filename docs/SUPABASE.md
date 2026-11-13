# Supabase Kalıcı Veritabanı (13.11.2026)

## Neden gerekliydi

Raporun P1-3 / Hata 5 bulgusu: GitHub Actions her çalıştığında **boş bir Postgres**
başlatıyordu. Dünkü fiyat olmadığı için `alert_changes.py` (`len(items) < 2`)
**hiçbir zaman fiyat değişikliği yakalayamıyordu** — yani uyarı e-postaları
aslında hiç gitmiyordu.

## Kurulan yapı

| Bileşen | Değer |
|---|---|
| Sağlayıcı | Supabase (ücretsiz katman) |
| Proje ref | `asplbobwuiqbsgayonxx` |
| Bölge | ap-southeast-1 |
| Postgres | 17.6 |
| Host | `aws-1-ap-southeast-1.pooler.supabase.com:5432` |
| Kullanıcı | `postgres.asplbobwuiqbsgayonxx` |
| Tablo | 10 (providers, models, price_observations, ...) |
| Veri | **1508 fiyat, 517 model, 5 sağlayıcı, 1 kur** |

## Önemli bulgu: proje INACTIVE idi

Proje Mart 2026'dan beri duraklatılmıştı (`INACTIVE`).
`POST /v1/projects/{ref}/restore` ile uyandırıldı → `ACTIVE_HEALTHY`.
Ücretsiz plan uzun süre kullanılmayan projeleri duraklatıyor.

## Fiyat değişim tespiti — düzeltilen hata

İlk yazdığım `v_price_changes` görünümü **aynı gözlemi** hem eski hem yeni sayıyordu:
```
deepseek-v4.1-flash: 1.5E-7 -> 1.5E-7  (%0.00)   <- YANLIŞ
```

Düzeltme: eski ve yeni **ayrı gözlemler** olmalı (`o.observed_at < n.observed_at`).

Doğrulama (simüle edilmiş fiyat düşüşü):
```
claude-fable-5.2: 12.00 -> 8.00  (%-33.33)   <- DOĞRU
```
(Simülasyon satırı sonra silindi.)

## CI akışı (yeni)

```
1) fiyatları topla (yerel, uçucu Postgres)
2) push_supabase.py      -> kalıcı geçmişe ekle (idempotent)
3) alert_changes_supabase.py -> v_price_changes'ten değişimleri oku
4) /api/bildir           -> onaylı abonelere e-posta
```

## Dosyalar

| Dosya | Görev |
|---|---|
| `db/supabase_schema.sql` | 10 tablo + `v_price_changes` görünümü |
| `scripts/push_supabase.py` | Günlük fiyatları Supabase'e yazar |
| `scripts/alert_changes_supabase.py` | Değişimleri Supabase'den okur |
| `.github/workflows/refresh.yml` | 13 adım (Supabase dahil) |

## Kimlik bilgileri

| Nerede | Ne |
|---|---|
| GitHub Secret | `SUPABASE_DB_PASSWORD` |
| GitHub Variable | `SUPABASE_PROJECT_REF` = `asplbobwuiqbsgayonxx` |
| Kod | Şifre **hiç yazılmadı**; yalnızca env'den okunur |

## Doğrulama

```
Bağlantı: PostgreSQL 17.6
Şema: 10 tablo oluştu
Migrasyon: 1508 fiyat, 517 model, 5 sağlayıcı
push_supabase.py: idempotent (ikinci çalıştırma satır çoğaltmadı)
alert_changes_supabase.py: 1 değişim okundu (12.0 -> 8.0)
216 test geçiyor
```

## Yapılan hata ve düzeltmesi

Test verisini temizlerken `where observed_at < now() - interval '1 day'`
koşulu **1495 gerçek satırı da sildi** (tüm gözlemler 11-13 Kasım'a ait).
Veri `_sbfast.py` ile yeniden yüklendi; şu an 1508 satır tam.

**Ders:** üretim verisinde `delete` yerine hedefli `id` kullanılmalı.

## Kalan iş

İlk gerçek günlük fark, yarınki (veya 6 saat sonraki) toplamadan sonra oluşacak.
O ana kadar `v_price_changes` boş döner — bu **doğru davranış** (tek gözlem var).
