# Bu Veriden Para Kazanma Planı

> Veri hazır: 5 sağlayıcı, 493 model, 1.528 onaylı fiyat gözlemi, tarihli USD/TRY kuru,
> kaynak URL'leri ve QA kayıtları. Aşağıdaki sıra "en hızlı nakit" → "en yüksek tavan".

## 0. Neden bu ürün satar (Türkiye gerçeği)

- Türk şirketleri AI bütçesini **USD** öder ama **TL** bütçeler. Kur 50 TL/$, yani 1 ABD doları
  mertebesindeki fiyat farkları aylık binlerce TL demek.
- Sağlayıcı fiyat sayfaları sürekli değişiyor (bu raporda Gemini'nin 4 modeli için 1 Aralık 2026'da
  yürürlüğe girecek zamlı fiyatlar tespit edildi). Kimse elle takip etmiyor.
- Kimse "kaynaklı" fiyat sunmuyor: herkes blog yazısı veya ekran görüntüsü paylaşıyor.

## A. Hemen (0–2 hafta): ücretsiz lead magnet + danışmanlık

**Ürün:** "Türkiye AI API Maliyet Endeksi — Kasım 2026" (Excel + 2 sayfa PDF özet).
**Fiyat:** ücretsiz PDF, 149 TL Excel paketi (kaynaklı, formüllü, güncelleme aboneliği).

Bunu satmak için gereken tek şey: LinkedIn/X'te paylaşılan tek bir tablo.

Örnek kanca (bu veriden):
> Aynı iş yükü (100M girdi + 25M çıktı token/ay) için Claude Sonnet 4.5 = **33.901 TL/ay**,
> DeepSeek V4-Pro = **5.801 TL/ay**. Aradaki **28.100 TL** yalnızca model seçimi.
> Kaynak: 5 sağlayıcının resmî fiyat sayfaları, 11.11.2026.

Hedef: 30 günde 300 indirme → %5 dönüşüm = 15 × 149 TL ≈ **2.235 TL** (mütevazı, ama liste başlatır).
Asıl kazanç: liste. Danışmanlık teklifi bu listeden çıkar.

**Danışmanlık paketi:** "AI maliyet denetimi" — 1 hafta, 9.000–15.000 TL.
Çıktı: mevcut kullanım envanteri + bu rapordaki tablo + 3 senaryolu tasarruf planı.
Tipik bulgu: %50–90 model maliyeti tasarrufu; müşteriye 12 ayda 100.000+ TL kazandırır, ücreti
tasarrufun ilk 1–2 ayı kadar. 2 müşteri = **~20.000 TL**.

## B. 1–3 ay: abonelikli veri (SaaS/API)

**Ürün:** `GET /api/v1/prices` + günlük güncelleme + fiyat değişikliği webhook'u.
**Fiyat:** 399 TL/ay (bireysel), 1.490 TL/ay (şirket, geçmiş + TRY + uyarı).

Neden satar: bir SaaS ürününe fiyat tablosu gömen her ekip bunu elle güncelliyor. Otomatik,
kaynaklı, geçmişi olan tek kaynak olmak yeterli değer.

Gereken ek iş (V0.2, ~2 hafta):
1. `approved` sonrası diff → e-posta/Slack/webhook uyarısı (fiyat %X değişti).
2. API anahtarı + kota (basit: `api_keys` tablosu).
3. TRY kuru ve "kaynaklı" alıntı sayfası (her fiyatın yanında kaynak linki + gözlem zamanı).

25 abone × 399 TL = **~10.000 TL/ay** tekrarlayan gelir. Hedef ilk 90 gün: 25 abone.

## C. 3–12 ay: en yüksek tavan

1. **Kurumsal lisans / veri besleme** — 25.000–60.000 TL/yıl; fiyat verisini kendi panolarına
   çekenler (ajanslar, bulut danışmanları, fintech'ler).
2. **"AI bütçe kalkanı" raporu** — aylık otomatik PDF; CFO'ya giden, "bu ay %12 zam geldi,
   taşırsan aylık 14.000 TL tasarruf" diyen abonelik (999 TL/ay).
3. **Türkçe token maliyeti karşılaştırması** — Türkçe metin, İngilizceye göre %20–60 daha fazla
   token harcıyor. Bunu ölçüp yayınlamak, bu pazarda kimsenin yapmadığı ve herkesin merak ettiği
   bir içerik; hem SEO hem danışmanlık motoru.

## D. Fiyatlandırma mantığı

| Katman | Fiyat | Kim öder | Neden |
|---|---|---|---|
| Rapor (tek seferlik) | 149 TL | bireysel geliştirici | anında değer, düşük sürtünme |
| Abonelik (veri) | 399 TL/ay | küçük ekip | tabloyu elle güncellemekten kurtarır |
| Abonelik (şirket) | 1.490 TL/ay | ürün/FinOps ekibi | geçmiş + TRY + uyarı + API |
| Denetim | 9.000–15.000 TL | KOBİ | tasarrufun 1–2 ayı |
| Yıllık lisans | 25.000–60.000 TL | ajans/kurumsal | kendi ürününe gömer |

Gerçekçi 12 ay: 2 denetim (20.000) + 25 abone × 12 ay ortalama (≈120.000) + 1 yıllık lisans
(35.000) ≈ **175.000 TL**. Tek kişilik operasyonla, sıfır reklam bütçesiyle.

## E. Bugün yapılacak 5 iş

1. `reports/AI_Maliyet_Raporu_2026-11-11.xlsx` → PDF'e çevir, ilk 2 sayfayı ücretsiz dağıt.
2. LinkedIn'e tek tablo + tek cümle kanca koy, yorumlarda Excel linki ver.
3. 10 Türk AI girişimine (kendi ürününde LLM kullanan) doğrudan mesaj: "Ücretsiz 1 sayfalık
   maliyet karşılaştırması göndereyim mi?"
4. `savings.py`'yi web sayfasına çevir (tek HTML + API çağrısı) → SEO trafiği yakalar.
5. Haftalık `run_collect.ps1` + `approve.py --auto` görevini Windows Task Scheduler'a ekle
   (veri taze kalsın, "güncel" iddiası kanıtlı olsun).

## F. Riskler ve dürüst uyarılar

- **Doğruluk iddiası en büyük sermayedir.** Fiyat değişimini %50'den fazla görünce otomatik onay
  durur; bu bilinçli. Yanlış fiyat yayınlamak, ürünü bitirir.
- Sağlayıcılar fiyat sayfası yapısını değiştirir; collector "partial" döner ve uyarır. Ayda bir
  `run_collect.ps1` çıktısını gözle kontrol et.
- Reklam/SEO geliri bu işin çekirdeği değil; **güvenilir veri + dağıtım** çekirdeği.
- Ödeme/üyelik altyapısı henüz yok (V0.1 kapsam dışı). İlk satışları havale/fatura ile yap,
  talep kanıtlanınca ödeme altyapısına yatırım yap.
