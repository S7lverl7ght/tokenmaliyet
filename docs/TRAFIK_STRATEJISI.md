# Trafik Stratejisi (19.11.2026)

## Sorun: site trafik çekmiyor

Ölçüm sonucu: teknik SEO **temiz**, ama trafik yok. Nedenleri:

| Bulgu | Ölçüm |
|---|---|
| İndekslenebilir sayfa | 133 (şimdi 175) |
| İngilizce karşılaştırma sayfası | **0** (şimdi 32) |
| RSS beslemesi | **yok** (şimdi var) |
| Anlamsız karşılaştırma sayfası | 40/61 (temizlendi) |

Teknik hata yoktu; **içerik ölçeği ve dağıtım kanalı** eksikti.

## Yapılanlar

### 1. Karşılaştırma sayfaları nitelikli hale getirildi
Önce 61 çift üretiliyordu ama 40'ı anlamsızdı:
```
gemini-2.5-flash-lite vs gemini-3-pro-image   ← biri sohbet, diğeri görsel model
```
Artık yalnızca **aynı işi gören** modeller karşılaştırılıyor (sohbet↔sohbet).
Sonuç: 32 anlamlı çift, hepsi arama talebi olan kombinasyonlar.

### 2. İngilizce karşılaştırma sayfaları (32 yeni sayfa)
Global aramada "claude vs gpt pricing" gibi sorgular Türkçe'den **10–20 kat** fazla
aranır ve RPM'i daha yüksektir. `/en/karsilastir/<slug>/` üretiliyor.

### 3. RSS beslemesi
`/rss.xml` — 19 öğe (fiyat hareketleri + karşılaştırmalar). Okuyucu uygulamaları,
Google Discover ve otomasyon araçları için gerçek dağıtım kanalı.

### 4. Sitemap tutarsızlığı giderildi
61 karşılaştırma sayfası varken sitemap 22 gösteriyordu (iki ayrı kod yolu).
Artık tek kaynak: `app/web/compare_pairs.py`.

## Trafik için sıradaki adımlar (sizin yapmanız gerekenler)

Bunlar kod ile çözülemez; hesap/başvuru gerektirir:

### Öncelik 1: Google Search Console
1. `sitemap.xml` yeniden gönderin (175 URL).
2. **URL Denetimi** → yeni 32 EN karşılaştırma sayfası için "Dizine eklenmesini iste".
3. "Sayfalar" raporunda *Keşfedildi – dizine eklenmedi* varsa toplu indeksleme isteyin.

### Öncelik 2: Backlink (en etkili tek faktör)
Site hiçbir yerden bağlantı almıyor. Ücretsiz ve hızlı:
- **Hacker News**: "Show HN: I built a free AI API price comparison with source URLs"
- **Reddit**: r/LocalLLaMA, r/MachineLearning (değer katan gönderi, reklam değil)
- **GitHub**: README'ye "Data source" olarak ekleyin
- **Dev.to / Medium**: "I compared 470 LLM prices" gibi bir yazı

### Öncelik 3: Dizin kayıtları
- alternativeto.net (fiyat karşılaştırma kategorisi)
- producthunt.com
- AI araç dizinleri (theresanaiforthat.com vb.)

### Öncelik 4: AdSense başvurusu
Yasal sayfalar, 400+ kelime teknik içerik ve sıfır kopya başlık hazır.
`adsense.google.com` → site ekle → `ca-pub` kimliğini al.

## Gerçekçi beklenti

Yeni bir site için organik trafik **3–6 ay** içinde gelir. İlk ay 0–50 ziyaret normal.
En hızlı kazanç: **backlink** + EN içerik. Reklam geliri için ~10.000 aylık görüntülenme
gerekir; bu, 3–6 ay düzenli içerik + backlink ile ulaşılabilir.

## Ölçüm

- Cloudflare Analytics: ziyaretçi, ülke, sayfa
- Search Console: gösterim, tıklama, ortalama pozisyon
- `/rss.xml` çekme sayısı (Cloudflare logs)

Haftalık kontrol: Search Console → Performans → hangi sorgular geliyor?
Gelen ama karşılanmayan sorgular = yeni sayfa fikri.
