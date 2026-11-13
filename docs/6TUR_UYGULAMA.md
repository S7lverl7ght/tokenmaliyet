# 6. Tur Denetim — Uygulama Raporu (13.11.2026)

Kaynak: `6TUR_DENETIM_VE_GELISTIRME_RAPORU.md`
Sonuç: **7/7 hata + 4 SEO bulgusu kapatıldı** · 226 test · canlı 10/10

---

## Önce ölçtüm, sonra düzelttim

Rapordaki her iddiayı koda karşı doğruladım. **Hepsi doğruydu** — uydurma
bulgu yoktu. Aşağıda her biri için kanıt ve düzeltme var.

---

## HATA-1 · PAT sızıntısı (P0) ✅

**Doğrulama:** `_ci3.py` içinde açık metin `ghp_...` token vardı.

**Ek kontrol:** Git geçmişinde var mı? → `git grep` tüm 66 commit'te **YOK**.
`.gitignore` içindeki `_*.py` kuralı korumuş. Yani sızıntı yalnızca diskteydi.

**Düzeltme:** Token `os.getenv('GITHUB_TOKEN')` ile değiştirildi. Tüm proje
tarandı: **0 PAT kaldı**. `test_no_hardcoded_pat_in_project` bunu kilitliyor.

---

## HATA-2 · `/hesaplayici` sitemap'te yok ✅

**Doğrulama:** `urls` listesi `["/", "/fiyatlar", ...]` — `/hesaplayici` yoktu.
Bu kritikti: `/` zaten `/hesaplayici`'ye yönlendiriyor.

**Düzeltme:** Listeye eklendi. Canlı sitemap'te doğrulandı.

---

## HATA-3 · `<lastmod>` basılmıyor ✅

**Düzeltme:** `lastmod` artık **gerçek veriden** geliyor:
`max(PriceObservation.observed_at)`. Uydurma tarih yok — veri yoksa bugünün
tarihine düşüyor.

```xml
<loc>https://tokenmaliyet.com/hesaplayici</loc><lastmod>2026-11-12</lastmod>
```

---

## HATA-4 · `og:image` eksik ✅

**Düzeltme:**
- `backend/app/web/static/og-image.png` üretildi (Pillow, **1200×630**, 21 KB)
- `og:image` + `og:image:width/height/alt` + `twitter:card=summary_large_image`
- `og:locale` artık dile göre (`tr_TR` / `en_US`)

Görsel: indigo gradyan, yükselen çubuk logosu, marka adı, slogan.

---

## HATA-5 · Tema butonunda yanlış tooltip ✅

**Doğrulama:** `title="{{ t('common.language') }}"` — gerçekten 'Dil' yazıyordu.

**Düzeltme:** `t('theme.toggle')`.

---

## HATA-6 · Çift arama kutusu ✅

**Doğrulama:** `#q` (sunucu formu) + `#live-q` (JS paneli) yan yana.
Statik sitede `#q` çalışmıyordu (query string işlenmiyor).

**Düzeltme:** Tek kutu. `#q` artık JS ile **tüm 471 modelde** arıyor;
JS yoksa klasik GET olarak çalışır. Sonuçlar `#live-results`'a basılıyor.

---

## HATA-7 · `_redirects` yerine meta refresh ✅

**Doğrulama:** `dist/_redirects` yoktu; yalnızca meta refresh vardı.

**Düzeltme:**
```
# dist/_redirects
/                /hesaplayici/    301
```
Meta refresh yalnızca `_redirects` desteklemeyen yerel önizleme için yedek
olarak kaldı; canonical artık `/hesaplayici/`.

---

## SEO-5 · İngilizce sayfalar sitemap'te yok ✅ — ve daha büyük bir hata bulundu

**Düzeltme:** `/en/fiyatlar`, `/en/hesaplayici`, `/en/karsilastir`,
`/en/token-sayaci`, `/en/gpu-maliyetleri`, `/en/hakkinda` eklendi.

### Bulduğum gerçek hata

Sitemap'e ekledikten sonra testler kırıldı: **`/en/...` yolları dinamik
sunucuda 404 veriyordu.** Statik export bu sayfaları üretiyordu ama FastAPI'de
karşılık gelen rota yoktu.

**Düzeltme:** `_register_variants()` — `/en/<sayfa>`, `/try/<sayfa>`,
`/en/try/<sayfa>` rotaları eklendi (dil/para birimi zaten `_parse_path` ile
yoldan çözülüyor).

```
/en/fiyatlar       200    /try/fiyatlar       200
/en/hesaplayici    200    /en/try/fiyatlar    200
/en/karsilastir    200    /en/gpu-maliyetleri 200
14/14 rota OK
```

**Not:** `/en/uyari` bilinçli olarak noindex (form sayfası) — sitemap'e
**eklenmedi**. Test bunu yakaladı, doğru davranış.

---

## Yaptığım hata (dürüstçe)

`sqlfunc` importunu eklediğimi sandım ama `edit` CRLF nedeniyle uygulanmamıştı.
Export `NameError` verdi. **Kontrol etmeden ilerledim.** Ders: her yamadan
sonra `grep` ile doğrula.

---

## Doğrulama

```
226 passed, 6 skipped          (önce 216)
Canlı kabul testi: 10/10
  /hesaplayici sitemap       PASS
  lastmod                    PASS
  en varyant                 PASS
  en/uyari YOK               PASS
  og:image                   PASS
  og-image.png 200           PASS
  tek arama kutusu           PASS
  /en/fiyatlar canlı         PASS
```

## Yeni testler

`tests_nodb/test_audit_round6.py` — 11 test, her biri bir rapor maddesini
kilitler (PAT taraması, sitemap içeriği, og-image boyutu, tooltip, tek arama,
`_redirects`).

## Kalan iş (rapordan)

| Madde | Durum |
|---|---|
| P1-3 danışmanlık hızlı formu | Yapılmadı (lead toplama backend'i gerekir) |
| P2-6 affiliate kodları | Kullanıcı başvurusu bekliyor |
| P2-7 Shopier ödeme | Ticari karar |
| PAT iptali / yeni token | **Kullanıcı yapmalı** (panel işlemi) |
