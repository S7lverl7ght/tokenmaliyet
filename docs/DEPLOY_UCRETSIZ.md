# Ücretsiz / Minimum Maliyetli Deploy Planı

Araştırma: 12.11.2026 · Kaynaklar resmî dokümantasyon (aşağıda bağlantılı)

## Özet: önerilen yol

| Katman | Seçim | Aylık maliyet |
|---|---|---|
| **Ana site** (fiyat listesi, rehber, model sayfaları) | Statik HTML → **Cloudflare Pages** | **0 ₺** |
| **Dinamik kısımlar** (hesaplayıcı sonucu, uyarı formu, API) | Cloudflare Workers Functions (Pages Functions) | **0 ₺** (100.000 istek/gün) |
| **Veritabanı** | Oracle Cloud **Always Free** (Autonomous DB veya A1 VM üstünde PostgreSQL) | **0 ₺** |
| **Veri yenileme** | **GitHub Actions** (public repo) | **0 ₺** |
| **Alan adı** | Tek gerçek gider | ~10–12 $/yıl |
| **E-posta gönderimi** | Resend / Brevo ücretsiz katman (100–300/gün) | **0 ₺** |

**Toplam: yalnızca alan adı.** İlk ay için başka zorunlu gider yok.

---

## 1. Cloudflare Pages — ücretsiz katman (resmî)

| Kalem | Free plan |
|---|---|
| Statik varlık istekleri | **Ücretsiz ve sınırsız** |
| Build sayısı | **500/ay** |
| Eşzamanlı build | 1 |
| Build zaman aşımı | 20 dakika |
| Preview deployment | Sınırsız |
| Özel alan adı | Var (SSL dahil) |
| Header kuralı | 100 satır, satır başına 2.000 karakter |

Kaynak: <https://developers.cloudflare.com/pages/platform/limits/>,
<https://developers.cloudflare.com/pages/functions/pricing/>

**Pages Functions** ücretsiz katmanı **Workers Free** kotasına sayılır:
**100.000 istek/gün** (Functions + Workers toplamı), gece yarısı UTC'de sıfırlanır.
Bu site için fazlasıyla yeterli: statik sayfalar bu kotayı **hiç** tüketmez.

> Not: Bizim sitemiz şu an sunucu-render (Jinja2 + FastAPI). Cloudflare Pages'e çıkmak için
> iki seçenek var: (a) statik export + Functions'a taşınan 4 dinamik uç, (b) mevcut FastAPI'yi
> küçük bir VM'de tutmak. Aşağıda (a) anlatılıyor; (b) yedek plan.

## 2. GitHub Actions — ücretsiz (public repo)

GitHub'ın "included compute usage" tablosuna göre GitHub Free için aylık **$12** değerinde
hesaplama dahil (private repo). **Public repository'de Actions dakikaları ücretsizdir.**

Kaynak: <https://docs.github.com/en/billing/reference/product-usage-included>

Bizim kullanım: günde 2 kez fiyat toplama + commit. Yaklaşık **60 dakika/ay**.
Public repoda bu **0 $**.

## 3. Oracle Cloud Always Free — veritabanı

Resmî "Always Free Resources" sayfasına göre süresiz ücretsiz:

- **2 × VM.Standard.E2.1.Micro** (AMD) VM
- **Ampere A1 Flex**: ayda **1.500 OCPU-saat + 9.000 GB-saat** = pratikte **2 OCPU / 12 GB RAM**
- **200 GB** Always Free blok depolama (boot volume için)
- **2 × Autonomous Database** (Always Free)
- 10 GB object storage (Standard) + 10 GB (Infrequent) + 10 GB (Archive)

Kaynak: <https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm>

**Bizim için anlamı:** A1 Flex VM'e PostgreSQL 18 + FastAPI kurulabilir; 12 GB RAM ve
2 OCPU bu iş yükü için fazlasıyla yeterli. Ya da Autonomous DB kullanılıp uygulama
Cloudflare Workers'a taşınır.

> Dikkat: Oracle Always Free hesapları **kullanılmayan kaynakları geri alabilir** (idle
> reclaim). Bot her gün çalıştığı için site "kullanılıyor" sayılır; yine de aylık kontrol edin.

## 4. Karşılaştırma: diğer ücretsiz seçenekler

| Sağlayıcı | Ücretsiz katman | Bizim için uygun mu? |
|---|---|---|
| **Cloudflare Pages** | Statik sınırsız, 100k req/gün | ✅ Ana site için en iyi |
| **GitHub Pages** | Statik, 100 GB/ay bant genişliği | ✅ Alternatif, ama Functions yok |
| **Vercel Hobby** | 100 GB bant, serverless | ⚠️ Ticari kullanım kısıtlı |
| **Netlify Free** | 100 GB, 125k function çağrısı/ay | ✅ Alternatif |
| **Fly.io** | Pay-as-you-go, ücretsiz katman kaldırıldı | ❌ |
| **Railway** | 5 $ deneme kredisi | ❌ |
| **Render Free** | 750 saat/ay, 15 dk uyku | ⚠️ Uyku sorunu |
| **Oracle Always Free** | 2 VM + 2 DB, süresiz | ✅ DB/API için en iyi |

## 5. Uygulama sırası

### Adım 1 — Statik export (bu depoda hazır)
```powershell
python scripts/export_static.py
# -> dist/ : tüm herkese açık sayfalar HTML olarak
```
Export, her sayfayı **sunucunun ürettiği HTML** olarak kaydeder. Böylece:
- Google/AI botları veriyi HTML'de görür (raporun "JS ile çiziliyor" itirazı kalkar)
- Cloudflare Pages statik olarak servis eder → **0 ₺, çok hızlı**
- LCP/CLS otomatik iyileşir

### Adım 2 — Dinamik uçlar
Statik export'ta kalan 3 dinamik iş var:
1. `/api/v1/*` (JSON)
2. `/uyari` POST (e-posta kaydı)
3. `/hesaplayici` ve `/token-sayaci` **zaten tarayıcıda** çalışıyor (JS) — sunucu gerekmez

1 ve 2 için Cloudflare Worker (Functions) yeterli. Alternatif: Oracle VM'de mevcut FastAPI.

### Adım 3 — Veri yenileme
```yaml
# .github/workflows/refresh.yml
on:
  schedule: [{cron: "10 3,15 * * *"}]   # 06:10 ve 18:10 TR
  workflow_dispatch:
```
Bot çalışır → JSON üretir → commit → Cloudflare Pages otomatik yeniden deploy.

### Adım 4 — Alan adı + DNS
Cloudflare Registrar veya herhangi bir kayıt firması. NS'leri Cloudflare'e yönlendir,
Pages projesine custom domain ekle. **SSL otomatik.**

## 6. Güvenlik kapısı (ücretsiz araçlar)

| Gereksinim | Ücretsiz çözüm |
|---|---|
| Admin paneli koruması | Cloudflare Access (50 kullanıcıya kadar ücretsiz) vb. |
| Bot koruması | **Cloudflare Turnstile** (ücretsiz) |
| Hız limiti | Cloudflare WAF rate limiting (ücretsiz plan sınırlı) |
| Analitik (çerezsiz) | **Cloudflare Web Analytics** (ücretsiz, KVKK dostu) |
| Secret tarama | gitleaks (GitHub Action) |
| Bağımlılık tarama | Dependabot + `pip-audit` |
| ZAP taraması | OWASP ZAP baseline (haftalık GitHub Action) |

## 7. Maliyet senaryoları

| Senaryo | Aylık | Not |
|---|---|---|
| **Minimum** (bu plan) | **0 ₺** + alan adı | Cloudflare Pages + GitHub Actions + Oracle DB |
| Konforlu | ~5 $ | Küçük VPS (Hetzner CX22) — tek makinede her şey |
| Ölçekli | ~20 $ | Yönetilen PostgreSQL + CDN |

## 8. Karar: hangisi?

**Şimdi:** Statik export + Cloudflare Pages. Veri günlük botla yenileniyor, site statik.
Dinamik gereken tek şey e-posta formu; o gelene kadar form Oracle VM'deki FastAPI'ye gidebilir
ya da geçici olarak devre dışı bırakılabilir.

**Neden VPS değil?** Sunucu bakımı, güncelleme, izleme yükü getirir. Statik site bunların
hiçbirini gerektirmez ve raporun istediği "hızlı, indekslenebilir" hedefini doğrudan karşılar.

**Neden Vercel/Netlify değil?** Ücretsiz katmanları ticari kullanımda sınırlı; Cloudflare
Pages ticari kullanıma açık ve sınırsız statik istek veriyor.
