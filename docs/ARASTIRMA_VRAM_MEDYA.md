# VRAM Hesaplayıcı ve Medya Maliyet Simülatörü — Gelir Araştırması

Tarih: 15.11.2026 · Kapsam: tokenmaliyet.com için A (VRAM/GPU uyumluluk) ve B (ses/görsel maliyet).

## 1. Gerçek arama talebi

Mutlak hacim verisi **bulamadım**: Ahrefs/Semrush/Ubersuggest 401/403, Similarweb 403. Aşağıdakiler Google Trends (12 ay, dünya) **göreli** endeksidir.

Aynı sette (12 ay ort.): `runway pricing` 54 · `midjourney pricing` 56 · `elevenlabs pricing` 22–35 · `kling ai pricing` 34 · `sora pricing` 23 · `ai image generator cost` 26 · `ai voice generator` 74
`vram calculator` **2,5–9,6** · `gpu memory calculator` 1,3–3,4 · `llm vram calculator` 1,3 · `how much vram for 70b model` 0,1

Medya fiyat sorguları VRAM sorgularının **~10–20 katı**. VRAM'de niyet daha net: autocomplete'te `vram calculator llm`, `vram calculator local llm`, `how much vram do i need` gerçek sorgular.

**Türkiye kritik:** `vram hesaplama` = 0,0 · `yapay zeka maliyet hesaplama` = 0,0 · `gpu kiralama` 0,6. `seslendirme yapay zeka` ise 51,5. Türkçe tarafta A için talep **yok**, B'nin ses ayağı için **var**.

## 2. Rekabet

**A — kalabalık ama hepsi yeni.** Tek DuckDuckGo SERP'inde 8 rakip (promptquorum, computingforgeeks, llmvramcalculator, llmhardware.io, mljourney, modelfit.io, convly.ai, layer3labs). RDAP kayıtları hepsinin **2026 içinde** olduğunu gösteriyor (modellens.ai 12.02 → modelvram.com 27.09). Otorite kurulmamış; giriş hızlı. Gerçek aslan: Hugging Face'in `hf-accelerate/model-memory-usage` Space'i (1.020 beğeni).

**B — daha az ve daha zayıf rakip**: aicostcalculators.com, ranthis.com, induwara.lk, aiaudiocosts.fyi — hepsi tek sayfalık, markasız.

## 3. Para gerçekten çıkıyor mu?

Oranlar doğrulandı: RunPod 10$ harcamada 5–500$ kredi + 6 ay %3 Pod/%5 Serverless, 25 referansla %10 nakit. Vast.ai **ömür boyu harcamanın %3'ü**, %75'i nakde. ElevenLabs **12 ay %22**. fal.ai H100 2,49–4,50$/sa.

Modelin çalıştığının kanıtı: localaipicks.com/rent-gpu, Vast/RunPod kodlarını açık affiliate tablosuyla yayınlıyor. **Ama VRAM hesaplayıcıların gerçek gelir rakamını bulamadım** — kamuya açık vaka yok.

Kritik matematik: Vast %3'üyle ayda 100$ için ~3.300$/ay GPU harcaması gerekir; RTX 4090 0,40$/saat ise **~8.200 GPU-saat/ay**. Bu, hesaplayıcı trafiğinden çıkmaz. ElevenLabs %22'de aynı 100$ için ~455$/ay abonelik yeter — **birim ekonomi B'de ~7 kat iyi**.

## 4. ROI

**B daha yüksek ROI, ama sadece ses ayağı**: (a) hacim 10–20 kat, (b) %22 komisyon, (c) TR'de tek talep burada. Video/görsel ayağı (Runway/Kling/FLUX) rekabetin en zayıf, dönüşümün en düşük yeri — erteleyin.

**A stratejik, finansal değil.** Trafiği az; ama mevcut 5 GPU sağlayıcısı veriniz onu bedavaya yakın yapıyor ve B2B "self-hosting maliyet analizi" danışmanlığına köprü kuruyor. Danışmanlık 9.000–15.000 TL ise tek müşteri, yıllık affiliate gelirinin tamamından fazla.

## 5. SEO

**Ayrı site açmayın; mevcut siteye alt sayfa ekleyin.** Site yeni ve düşük otoriteli, alan adı bölmek otoriteyi ikiye keser. `/hesaplayici` ve `/en/hesaplayici` zaten var → `/hesaplayici/vram` ve `/hesaplayici/ses-maliyeti`, TR+EN çift dilli.

Hedefler — A: `llm vram calculator`, `vram calculator local llm`, `70b model kaç gb vram`, `rtx 4090 hangi model`, `q4_k_m vram`. B: `elevenlabs cost per minute`, `tts maliyeti`, `1000 görsel maliyeti`.

## 6. Teknik doğruluk

```
VRAM ≈ ağırlıklar + KV cache + overhead
ağırlıklar (GB) = params(M) × bayt/param
KV cache (GB)  = 2 × katman × kv_head × head_dim × bağlam × batch × bayt / 1e9
overhead       ≈ 0,5–1,5 GB
```
bayt/param: FP16 **2,0** · INT8 **1,0** · Q8_0 **1,06** · Q5_K_M **0,70** · Q4_K_M **0,58** · Q3_K_M **0,40**.
Doğrulama: 7B Q4_K_M dosyası ~4,08 GB → 0,583 bayt/param; formül tutuyor. Llama-3 70B (80 katman, 8 KV head, head_dim 128, FP16) → token başına 0,31 MB; 32K bağlamda **~10 GB sadece KV cache** — 70B'yi 24 GB'da çalıştırmayı imkânsız kılan budur.

**2026 fiyatları:** ElevenLabs v4 0,08$/1K karakter, v4 Turbo 0,04$, Scribe STT 0,20$/saat. OpenAI tts-1 15$/1M karakter, tts-1-hd 30$, Whisper 0,006$/dk, gpt-transcribe 0,0045$/dk. FLUX 3 Image 0,041–0,10$/görsel, Klein 0,008$; FLUX 3 Video 0,15$/sn (HD). Runway kredi 0,01$: kling3.0_standard 0,09$/sn, pro 0,12$, 4K 0,43$, seedance2_5 1080p 0,68$/sn. Sora API fiyatı OpenAI tablosunda **yok** — bulamadım.

**Kendi verinizle çapraz kontrol (Vast.ai, 12.11.2026):** RTX 4090 0,40$/sa · RTX 5090 0,67$ · A100 80GB 0,46$ · L40S 48GB 0,43$ · H100 NVL 2,47$ · B200 6,25$.

## TAVSİYE: Kısmen ekle — B'nin ses ayağı hemen, A 2. fazda

1. **Şimdi (1 hafta):** `/hesaplayici/ses-maliyeti` — ElevenLabs %22 + OpenAI TTS/Whisper karşılaştırması, TR+EN. En iyi birim ekonomi, TR'de tek gerçek talep, en zayıf rekabet.
2. **+2 hafta:** `/hesaplayici/vram` — formül yukarıda, GPU fiyatları elinizde; her GPU sayfasına (dist/gpu/*) "bu kartta hangi modeller çalışır" iç-linki verin. Trafik beklentisini düşük tutun; değeri danışmanlık hunisinde.
3. **Şimdilik eklemeyin:** video (Runway/Kling/FLUX/Sora) simülatörü — fiyatlar aylık değişiyor, dönüşüm düşük, bakım pahalı.
4. Affiliate sözleşmelerini yayından önce imzalayın; ama bu araçlar **nakit değil, danışmanlık lead'i** üretir. Gelir planını B2B danışmanlık üzerine kurmaya devam et.

## Kaynaklar
- https://www.runpod.io/referral-and-affiliate-program · https://docs.vast.ai/guides/reference/referral-program
- https://elevenlabs.io/affiliates · https://elevenlabs.io/pricing/api · https://platform.openai.com/docs/pricing.md
- https://bfl.ai/pricing · https://docs.dev.runwayml.com/guides/pricing/ · https://fal.ai/pricing
- https://github.com/ggml-org/llama.cpp/discussions/2094 · https://huggingface.co/spaces/hf-accelerate/model-memory-usage
- https://localaipicks.com/rent-gpu (affiliate model kanıtı)
- Veri: Google Trends/pytrends (12 ay, dünya + TR), RDAP kayıt tarihleri, yerel Vast.ai anlık görüntüsü (12.11.2026)
