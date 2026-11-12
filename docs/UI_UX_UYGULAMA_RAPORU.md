# UI/UX Yeniden Tasarim — Uygulama Raporu

Tarih: 11.11.2026 · Kilavuz: AI_Maliyet_Merkezi_UI_UX_Tasarim_Kilavuzu.md v1.0

## 1. Yaklasim

Kilavuz Next.js App Router oneriyor; projede framework yoktu. Onayinizla **statik SSR**
(Jinja2 + saf CSS) secildi. Gerekce: SEO kriterleri (sunucu-render HTML, canonical, sitemap,
structured data) framework olmadan da tam karsilaniyor; JS yuku kritik yolda yok, LCP icin
en iyi secenek. Etkilesim yogunlasirsa Faz 4te Next.js gecis yolu acik.

## 2. Degisen / eklenen dosyalar

### Yeni — tasarim temeli

| Dosya | Icerik |
|---|---|
| `backend/app/web/static/app.css` | Design tokens + 12 kolon grid + tum bilesen stilleri (22 KB) |
| `backend/app/web/static/favicon.svg` | Marka simgesi |
| `backend/app/web/templates/base.html` | Ortak kabuk: head/SEO/OG/schema, nav, footer, tema |
| `backend/app/web/templates/prices.html` | `/fiyatlar` |
| `backend/app/web/templates/model.html` | `/modeller/{provider}/{slug}` |
| `backend/app/web/templates/compare.html` | `/karsilastir` |
| `backend/app/web/templates/calculator.html` | `/hesaplayici` |
| `backend/app/web/templates/gpu.html` | `/gpu-maliyetleri` (bos durum) |
| `backend/app/web/templates/about.html` | `/hakkinda` (metodoloji) |
| `backend/app/web/templates/guide_base.html`, `guide_index.html` | `/rehber` |
| `backend/app/web/templates/rehber/*.html` | 3 ozgun rehber yazisi |
| `backend/app/web/templates/admin_login.html`, `admin_queue.html` | Korumali yonetim |
| `backend/app/web/templates/404.html` | Hata sayfasi |

### Yeni — Python

| Dosya | Icerik |
|---|---|
| `backend/app/web/queries.py` | Paylasilan veri katmani (slug, varyant, peak/off-peak) |
| `backend/app/web/render.py` | Jinja ortami, TR locale filtreleri, fiyat normalizasyonu |
| `backend/app/web/routes.py` | 10 SSR rotasi + sitemap/robots + `/api/v1/model-options` |
| `backend/app/web/admin.py` | Korumali kuyruk, onay/red, kaynak sagligi |
| `backend/app/web/content/guides.py` | Rehber kayitlari |

### Degisen

| Dosya | Degisiklik |
|---|---|
| `backend/app/main.py` | StaticFiles mount, web+admin router, `/` -> 302 `/fiyatlar` |
| `requirements.txt` | `jinja2`, `python-multipart` |
| `.env.example` | `ADMIN_TOKEN` |
| `tests/conftest.py` | Web testleri icin gercekci fikstur |
| `tests/test_web.py` | 49 yeni test |

**API sozlesmesi korundu.** Mevcut `/api/v1/*` uclari aynen calisiyor; yalnizca
`/api/v1/model-options` eklendi (yeni, kirici degil).

## 3. Kilavuz kriterleri — durum

| Kriter | Durum | Kanit |
|---|---|---|
| Acik tema varsayilan, koyu tema opsiyonel | EVET | `data-theme`, `localStorage` |
| 1280–1440 px kap, 12 kolon grid | EVET | `--container:1400px`, `.grid12` |
| Fiyat tablosu ana odak | EVET | Tam genislik, KPI 4 kucuk metrik |
| Hesaplayici ayri sayfa | EVET | `/hesaplayici`, formul + varsayimlar acik |
| Mobilde kart listesi | EVET | 375 px: `thead:none`, satirlar block, tasma yok |
| Design tokens | EVET | 40+ degisken |
| Tipografi olcegi | EVET | H1 32/40 -> xs 12 px |
| Tabular numerals | EVET | `.num`, `.cell-price` |
| WCAG 2.2 AA kontrast | EVET | 8 sayfada 0 ihlal (tarayicida olculdu) |
| Klavye + gorunur focus | EVET | `:focus-visible`, skip-link |
| `prefers-reduced-motion` | EVET | Var |
| Semantik tablo | EVET | `caption`, `scope`, `thead/tbody` |
| SEO title/description/canonical | EVET | Test edildi |
| Sitemap + robots | EVET | 500+ URL; `/admin` ve filtre URL engelli |
| Filtre URL noindex | EVET | Test: `?provider=`, `?page=3` |
| Admin noindex + korumali | EVET | `ADMIN_TOKEN` yoksa 403 |
| Structured data | EVET | WebSite, BreadcrumbList |
| Sahte veri yok | EVET | GPU sayfasi bos durum; sayilar DBden |

## 4. Test ciktisi

```
56 passed, 1 warning in 1.75s
```

Dagilim: 7 mevcut (pipeline/API) + 49 yeni web testi (sayfa 200, tek H1, title/description,
canonical, noindex kurallari, robots, sitemap, form etiketleri, hesaplayici dogrulama, 404).

## 5. Olculen degerler

| Sayfa | HTML (once) | HTML (sonra) |
|---|---|---|
| `/hesaplayici` | 134 KB | **24 KB** |
| `/karsilastir` | 255 KB | **33 KB** |
| `/fiyatlar` | 94 KB | 94 KB (50 satir/sayfa) |

Model listesi sunucudan gomulmuyor; `/api/v1/model-options` (58 KB) JS ile yalnizca
gerektiginde yukleniyor. JS kapaliysa sayfa dogrudan API modelleriyle calisir.

Kontrast denetimi (tarayicida hesaplandi): `muted` #64748B -> **#5A677C**
(#FFF ve #F1F5F9 uzerinde 4.5:1 ustu). Denetim sonrasi **0 ihlal**.

## 6. Ekran goruntuleri

- Fiyatlar (acik tema, 1440 px): 7 sutun, birim + TRY + dogrulama tarihi
- Fiyatlar (koyu tema): ayni yapi
- Fiyatlar mobil (375 px): kart listesi, tasma yok
- Hesaplayici: Claude Sonnet 4.5 -> DeepSeek V4-Pro = **%82,9 tasarruf**
- Karsilastir: 3 model yan yana, en dusuk maliyet isaretli
- Model detayi: peak + off-peak ayri satirlar, kaynak ve gecmis

## 7. Bilinen eksikler

1. **Kullanici testi yapilmadi** — kilavuz 5–8 kisiyle gorev testi istiyor.
2. **Lighthouse kosulmadi** — sunucu HTML tek istek + 22 KB CSS (JS kritik yolda yok);
   LCP hedefte olmasi beklenir ama olculmedi.
3. **`/fiyatlar` 94 KB** — 50 satir x 7 sutun. Sanallastirma veya 25 satir secenegi var.
4. **Rehber icerigi 3 yazi** — kapsam genisletilebilir.
5. **GPU sayfasi bos** — veri hatti yok; "ornek fiyat uydurma" yasagi geregi bilincli bos.
6. **Onay arayuzu** basit (onayla/reddet). Toplu islem ve diff V0.2.
7. **`og:image` yok** — paylasim gorseli sablonu uretilmedi.

## 8. Calistirma

```powershell
cd C:\AI-Maliyet-Merkezi
$env:PYTHONPATH="$PWD\backend"
$env:ADMIN_TOKEN="guclu-bir-anahtar"
.\run_api.ps1
# http://127.0.0.1:8000/fiyatlar
```

Sayfalar: `/fiyatlar` `/modeller/{provider}/{slug}` `/karsilastir` `/hesaplayici`
`/gpu-maliyetleri` `/rehber` `/hakkinda` `/admin/kuyruk`
