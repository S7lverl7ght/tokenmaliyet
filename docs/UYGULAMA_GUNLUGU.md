# Uygulama Günlüğü (Özet)

Bu dosya, tek tek tur raporlarının yerini alır. Ayrıntılı tur dokümanları (`3TUR_...` – `10TUR_...`,
`INCELEME_UYGULAMA_RAPORU`, `EN_RAPOR_UYGULAMA`, `UI_UX_UYGULAMA_RAPORU`, `SURUM_NOTU_8_MADDE`,
`KABUL_KONTROL`) 16.11.2026'da silindi; kalıcı bilgi aşağıda toplandı.

## Durum (16.11.2026)

| Bileşen | Durum |
|---|---|
| Canlı site | https://tokenmaliyet.com (Cloudflare Pages) |
| Testler | 306 geçiyor, 6 atlandı |
| Sayfa sayısı | 490+ statik HTML |
| Veri | 5 sağlayıcı, ~470 model, ~1.500 onaylı fiyat gözlemi |
| Otomasyon | GitHub Actions: 6 saatte bir topla → doğrula → yayınla |
| Haftalık bülten | Pazartesi 09:00 TR (`bulten.yml`) |

## Tamamlanan turlar

| Tur | Kapsam | Sonuç |
|---|---|---|
| 3 | Doğrulama/yayınlama raporu | 126 test |
| 4 | Güvenlik + SEO + programatik sayfalar | GPU ailesi ve karşılaştırma sayfaları |
| 5–7 | Kapsamlı denetimler | Turnstile, CSP, çift onay, sitemap |
| 8 | Çeviri + medya maliyet + SEO başlık | 174→0 çevrilmemiş metin; ses/görsel hesaplayıcı |
| 9 | Gelir + SEO denetimi | Kanonik adresler, 17 ölü model sayfası, kullanım koşulları |
| 10 | Canonical / API / bülten | Gerçek API dokümantasyonu, çift onaylı bülten |

## Kilitli gerçek hatalar (regresyon testleri)

Aşağıdakilerin her biri `tests_nodb/test_audit_round*.py` içinde testle kilitlidir:

- Kanonik adresler trailing-slash biçiminde olmalı (Cloudflare 308 uyumu)
- EN sayfalarda Türkçe metin olmamalı (ASCII-only kelimeler dahil: `Pazaryeri`, `Temizle`)
- Tazelik rozeti ve kanal etiketleri dile duyarlı olmalı
- JSON-LD blokları geçerli JSON olmalı (Jinja `|tojson` öncelik tuzağı)
- İç bağlantıların hepsi 200 dönmeli (alias modeller linklenmemeli)
- Başlıklar benzersiz ve ≤60 karakter olmalı

## Operasyon rehberleri (korundu)

`DEPLOY.md` · `CRON_JOB_ORG.md` · `TURNSTILE.md` · `SUPABASE.md` · `ILETISIM_FORMU.md` ·
`UYARI_SISTEMI.md` · `UYARI_FORMU.md` · `GITHUB_CI_KURULUM.md` · `OTOMASYON_KURULUM.md` ·
`PC_KAPALI_CALISMA.md` · `GELIR_PLANI.md` · `ARASTIRMA_VRAM_MEDYA.md`

## Bilinen açık işler

- `AFFILIATE_ELEVENLABS`, `AFFILIATE_RUNPOD`, `AFFILIATE_VASTAI` — başvuru sonrası env'e girilecek
- AdSense başvurusu — yayıncı kimliği (`ca-pub`) gerekli
- Bülten listesi 0 abone; gönderim altyapısı hazır (`bulten-gonder`)
