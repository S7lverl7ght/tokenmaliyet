"""Basit iki dilli sozluk.

Kural: kullaniciya gorunen tum metinler burada tanimli olmak zorunda degil;
yaygin gezinme/baslik/etiketler cevrilir, uzun icerik (rehber) Turkce kalir.
Sayfa dili <html lang> olarak da yansitilir (SEO).
"""
from __future__ import annotations

DEFAULT_LANG = "tr"
SUPPORTED = ("tr", "en")

STRINGS: dict[str, dict[str, str]] = {
    # gezinme
    "nav.prices": {"tr": "Fiyatlar", "en": "Prices"},
    "nav.compare": {"tr": "Karşılaştır", "en": "Compare"},
    "nav.calculator": {"tr": "Hesaplayıcı", "en": "Calculator"},
    "nav.token": {"tr": "Token sayacı", "en": "Token counter"},
    "nav.gpu": {"tr": "GPU maliyetleri", "en": "GPU costs"},
    "nav.guides": {"tr": "Rehber", "en": "Guides"},
    "nav.about": {"tr": "Hakkında", "en": "About"},
    "nav.search": {"tr": "Model ara", "en": "Find a model"},
    "theme.toggle": {"tr": "Koyu temaya geç", "en": "Switch to dark theme"},
    "theme.toggle.light": {"tr": "Açık temaya geç", "en": "Switch to light theme"},
    "a11y.skip": {"tr": "İçeriğe geç", "en": "Skip to content"},

    # tablo
    "col.model": {"tr": "Model", "en": "Model"},
    "col.provider": {"tr": "Sağlayıcı", "en": "Provider"},
    "col.channel": {"tr": "Kanal", "en": "Channel"},
    "col.input": {"tr": "Girdi fiyatı", "en": "Input price"},
    "col.output": {"tr": "Çıktı fiyatı", "en": "Output price"},
    "col.updated": {"tr": "Güncelleme", "en": "Updated"},
    "col.source": {"tr": "Model sayfası", "en": "Model page"},

    # ortak
    "common.source": {"tr": "Kaynak", "en": "Source"},
    "common.clear": {"tr": "Filtreleri temizle", "en": "Clear filters"},
    "common.apply": {"tr": "Uygula", "en": "Apply"},
    "common.currency": {"tr": "Para birimi", "en": "Currency"},
    "common.language": {"tr": "Dil", "en": "Language"},

    # --- gezinme ek ---
    "nav.tools": {"tr": "Araçlar", "en": "Tools"},
    "nav.tr_difference": {"tr": "Türkçe token farkı", "en": "Turkish token gap"},
    "nav.changes": {"tr": "Değişiklikler", "en": "Changes"},
    "nav.menu": {"tr": "Ana menü", "en": "Main menu"},
    "nav.menu_open": {"tr": "Menüyü aç", "en": "Open menu"},
    "nav.menu_close": {"tr": "Menüyü kapat", "en": "Close menu"},
    "pref.label": {"tr": "Görüntüleme tercihleri", "en": "Display preferences"},

    # --- alt bilgi ---
    "footer.product": {"tr": "Ürün", "en": "Product"},
    "footer.data": {"tr": "Veri", "en": "Data"},
    "footer.legal": {"tr": "Yasal", "en": "Legal"},
    "footer.compare": {"tr": "Model karşılaştır", "en": "Compare models"},
    "footer.calculator": {"tr": "Maliyet hesaplayıcı", "en": "Cost calculator"},
    "footer.about": {"tr": "Hakkında ve metodoloji", "en": "About and methodology"},
    "footer.api_docs": {"tr": "API dokümantasyonu", "en": "API documentation"},
    "footer.contact": {"tr": "İletişim", "en": "Contact"},
    "footer.corrections": {"tr": "Düzeltmeler", "en": "Corrections"},
    "footer.privacy": {"tr": "Gizlilik", "en": "Privacy"},
    "footer.price_page": {"tr": "fiyat sayfası", "en": "pricing page"},
    "footer.disclaimer_title": {
        "tr": "Bağımsız bir fiyat karşılaştırma sitesidir; sağlayıcı değildir.",
        "en": "An independent price comparison site; not a provider.",
    },
    "footer.disclaimer_data": {
        "tr": "Fiyatlar resmî sağlayıcı sayfalarından otomatik toplanır, yayın öncesi doğrulama kontrolünden geçer.",
        "en": "Prices are collected automatically from official provider pages and pass a pre-publication verification step.",
    },
    "footer.disclaimer_warn": {
        "tr": "Veriler bilgilendirme amaçlıdır ve yatırım, hukuk veya mali müşavirlik tavsiyesi değildir.",
        "en": "Data is for information only and is not investment, legal or accounting advice.",
    },
    "footer.disclaimer_tax": {
        "tr": "Vergiler, kur farkları ve sözleşme koşulları nedeniyle gerçek fatura farklı olabilir.",
        "en": "Actual invoices may differ due to taxes, exchange rates and contract terms.",
    },
    "footer.disclaimer_estimate": {
        "tr": "Hesaplamalar tahmindir.",
        "en": "Calculations are estimates.",
    },
    "footer.report_error": {"tr": "Hatalı veri bildirimi için", "en": "To report incorrect data,"},
    "footer.last_check": {"tr": "Son veri kontrolü", "en": "Last data check"},
    "footer.no_cookies": {
        "tr": "Reklam ve izleme çerezi kullanılmaz",
        "en": "No advertising or tracking cookies",
    },

    # --- fiyat tablosu ---
    "prices.title": {"tr": "AI API fiyatları", "en": "AI API prices"},
    "prices.search": {"tr": "Model ara", "en": "Search models"},
    "prices.search_ph": {"tr": "Model veya sağlayıcı ara", "en": "Search model or provider"},
    "prices.kind": {"tr": "Model tipi", "en": "Model type"},
    "prices.kind.chat": {"tr": "Sohbet / metin", "en": "Chat / text"},
    "prices.kind.all": {"tr": "Tümü", "en": "All"},
    "prices.kind.embedding": {"tr": "Embedding", "en": "Embedding"},
    "prices.kind.image": {"tr": "Görsel", "en": "Image"},
    "prices.kind.audio": {"tr": "Ses", "en": "Audio"},
    "prices.sort": {"tr": "Sırala", "en": "Sort"},
    "prices.sort.popular": {"tr": "Önerilen", "en": "Recommended"},
    "prices.sort.in_asc": {"tr": "Girdi: düşük → yüksek", "en": "Input: low → high"},
    "prices.sort.in_desc": {"tr": "Girdi: yüksek → düşük", "en": "Input: high → low"},
    "prices.sort.out_asc": {"tr": "Çıktı: düşük → yüksek", "en": "Output: low → high"},
    "prices.sort.out_desc": {"tr": "Çıktı: yüksek → düşük", "en": "Output: high → low"},
    "prices.sort.name": {"tr": "Model A–Z", "en": "Model A–Z"},
    "prices.sort.recent": {"tr": "En yeni", "en": "Most recent"},
    "prices.channel": {"tr": "Kanal", "en": "Channel"},
    "prices.channel.all": {"tr": "Tümü", "en": "All"},
    "prices.channel.direct": {"tr": "Doğrudan API", "en": "Direct API"},
    "prices.channel.marketplace": {"tr": "Pazaryeri", "en": "Marketplace"},
    "prices.provider": {"tr": "Sağlayıcı", "en": "Provider"},
    "prices.provider.all": {"tr": "Tüm sağlayıcılar", "en": "All providers"},
    "prices.empty": {"tr": "Bu filtrelerle model bulunamadı.", "en": "No models match these filters."},
    "prices.per_million": {"tr": "1M token başına", "en": "per 1M tokens"},

    # --- ortak ---
    "common.yes": {"tr": "Evet", "en": "Yes"},
    "common.no": {"tr": "Hayır", "en": "No"},
    "common.close": {"tr": "Kapat", "en": "Close"},
    "common.loading": {"tr": "Yükleniyor...", "en": "Loading..."},
    "common.error": {"tr": "Bir hata oluştu.", "en": "An error occurred."},
    "common.retry": {"tr": "Tekrar dene", "en": "Try again"},
    "common.save": {"tr": "Kaydet", "en": "Save"},
    "common.saving": {"tr": "Kaydediliyor...", "en": "Saving..."},
    "common.estimate": {"tr": "tahmin", "en": "estimate"},
    "common.updated": {"tr": "güncel", "en": "current"},
    "common.last_48h": {"tr": "son 48 saat", "en": "last 48 hours"},
    "common.unknown": {"tr": "Bilinmiyor", "en": "Unknown"},

    # --- uyari formu ---
    "alert.title": {"tr": "Fiyat uyarısı", "en": "Price alert"},
    "alert.email": {"tr": "E-posta adresiniz", "en": "Your email address"},
    "alert.email_help": {
        "tr": "Yalnızca fiyat uyarısı için kullanılır; üçüncü taraflarla paylaşılmaz.",
        "en": "Used only for price alerts; never shared with third parties.",
    },
    "alert.threshold": {"tr": "Ne zaman haber vereyim?", "en": "When should I be notified?"},
    "alert.th_5": {"tr": "%5 veya daha fazla değişince", "en": "When it changes by 5% or more"},
    "alert.th_10": {"tr": "%10 veya daha fazla değişince", "en": "When it changes by 10% or more"},
    "alert.th_20": {"tr": "%20 veya daha fazla değişince", "en": "When it changes by 20% or more"},
    "alert.direction": {"tr": "Değişim yönü", "en": "Direction of change"},
    "alert.dir_down": {"tr": "Sadece ucuzlarsa", "en": "Only when it gets cheaper"},
    "alert.dir_up": {"tr": "Sadece pahalanırsa", "en": "Only when it gets more expensive"},
    "alert.dir_any": {"tr": "Her iki yönde", "en": "Either direction"},
    "alert.submit": {"tr": "Uyarı kaydet", "en": "Save alert"},
    "alert.sent_confirm": {
        "tr": "Onay e-postası gönderdik. Kaydınızı etkinleştirmek için e-postadaki bağlantıya tıklayın.",
        "en": "We sent a confirmation email. Click the link in it to activate your alert.",
    },
    "alert.saved_no_mail": {
        "tr": "Kaydınız alındı. E-posta gönderimi şu an kapalı; kayıt tutuldu.",
        "en": "Your alert was saved. Email delivery is currently off; the record was kept.",
    },
    "alert.err_generic": {
        "tr": "Kayıt alınamadı. Lütfen tekrar deneyin.",
        "en": "Could not save your alert. Please try again.",
    },
    "alert.err_network": {
        "tr": "Bağlantı hatası. İnternet bağlantınızı kontrol edip tekrar deneyin.",
        "en": "Connection error. Check your internet connection and try again.",
    },

    # --- hesaplayici ---
    "calc.title": {"tr": "Maliyet hesaplayıcı", "en": "Cost calculator"},
    "calc.from": {"tr": "Mevcut model", "en": "Current model"},
    "calc.to": {"tr": "Alternatif model", "en": "Alternative model"},
    "calc.in_tokens": {"tr": "Aylık girdi token", "en": "Monthly input tokens"},
    "calc.out_tokens": {"tr": "Aylık çıktı token", "en": "Monthly output tokens"},
    "calc.text_lang": {"tr": "Metin dili", "en": "Text language"},
    "calc.calc": {"tr": "Hesapla", "en": "Calculate"},
    "calc.result": {"tr": "Sonuç", "en": "Result"},
    "calc.current": {"tr": "Mevcut", "en": "Current"},
    "calc.alternative": {"tr": "Alternatif", "en": "Alternative"},
    "calc.monthly_diff": {"tr": "Aylık fark", "en": "Monthly difference"},
    "calc.yearly_diff": {"tr": "Yıllık fark", "en": "Yearly difference"},
    "calc.saving": {"tr": "Tasarruf", "en": "Savings"},
    "calc.cost_increase": {"tr": "Maliyet artışı", "en": "Cost increase"},
    "calc.cheaper": {"tr": "Alternatif daha ucuz", "en": "The alternative is cheaper"},
    "calc.pricier": {
        "tr": "Alternatif daha pahalı — bu bir tasarruf değildir",
        "en": "The alternative is more expensive — this is not a saving",
    },
    "calc.same": {"tr": "İki model aynı maliyette", "en": "Both models cost the same"},
    "calc.tr_assumption": {"tr": "Türkçe içerik varsayımı", "en": "Turkish content assumption"},
    "calc.tr_note": {
        "tr": "her iki modelin maliyeti de aynı Türkçe token çarpanıyla hesaplandı",
        "en": "both models are priced with the same Turkish token multiplier",
    },
    "calc.tr_estimate": {
        "tr": "Bu bir tahmindir; İngilizce karşılaştırması için yukarıdan dili değiştirin.",
        "en": "This is an estimate; switch the language above for an English comparison.",
    },
    "calc.scenarios": {"tr": "Örnek senaryolar", "en": "Sample scenarios"},
    "calc.detail": {"tr": "Hesap detayı", "en": "Calculation detail"},
    "calc.share": {
        "tr": "Bağlantıyı paylaşabilirsiniz: bu sayfanın adresi seçimlerinizi ve token hacminizi taşır. Hassas veri içermez.",
        "en": "You can share the link: this page's address carries your selections and token volume. It contains no sensitive data.",
    },

    # --- karsilastir ---
    "cmp.title": {"tr": "Model karşılaştır", "en": "Compare models"},
    "cmp.model_n": {"tr": "model", "en": "model"},
    "cmp.optional": {"tr": "(isteğe bağlı)", "en": "(optional)"},
    "cmp.select_none": {"tr": "— seçin —", "en": "— select —"},
    "cmp.not_selected": {"tr": "Seçilmedi", "en": "Not selected"},
    "cmp.input": {"tr": "Girdi", "en": "Input"},
    "cmp.output": {"tr": "Çıktı", "en": "Output"},
    "cmp.diff": {"tr": "Fark", "en": "Difference"},
    "cmp.last_verified": {"tr": "Son doğrulama", "en": "Last verified"},
    "cmp.best": {"tr": "en düşük maliyet", "en": "lowest cost"},
    "cmp.detail_link": {"tr": "Model detayı", "en": "Model details"},
    "cmp.at_least_two": {"tr": "En az iki model seçin.", "en": "Select at least two models."},
    "cmp.monthly_chart": {"tr": "Aylık maliyet karşılaştırması (USD)", "en": "Monthly cost comparison (USD)"},
    "cmp.direct": {"tr": "Doğrudan API", "en": "Direct API"},

    # --- token sayaci ---
    "tok.title": {"tr": "Token sayacı", "en": "Token counter"},
    "tok.paste": {"tr": "Metni buraya yapıştırın", "en": "Paste your text here"},
    "tok.count": {"tr": "token", "en": "tokens"},
    "tok.words": {"tr": "kelime", "en": "words"},
    "tok.chars": {"tr": "karakter", "en": "characters"},
    "tok.tr_or_en": {"tr": "Türkçe mi, İngilizce mi?", "en": "Turkish or English?"},
    "tok.sample": {"tr": "Örnek metin", "en": "Sample text"},

    # --- gpu ---
    "gpu.title": {"tr": "GPU kiralama maliyetleri", "en": "GPU rental costs"},
    "gpu.vram": {"tr": "VRAM", "en": "VRAM"},
    "gpu.lowest": {"tr": "En düşük fiyat", "en": "Lowest price"},
    "gpu.per_gb": {"tr": "$/GB VRAM", "en": "$/GB VRAM"},
    "gpu.provider": {"tr": "Sağlayıcı", "en": "Provider"},
    "gpu.kind": {"tr": "Tip", "en": "Type"},
    "gpu.range": {"tr": "On-demand aralık", "en": "On-demand range"},
    "gpu.monthly": {"tr": "ay", "en": "mo"},
    "gpu.hour": {"tr": "saat", "en": "hour"},

    # --- ek: hesaplayici detay ---
    "calc.cache": {"tr": "Önbellek oranı", "en": "Cache ratio"},
    "calc.advanced": {"tr": "Gelişmiş", "en": "Advanced"},
    "calc.summary": {"tr": "girdi +", "en": "input +"},
    "calc.output": {"tr": "çıktı token", "en": "output tokens"},
    "calc.per_month": {"tr": "/ ay", "en": "/ mo"},
    "calc.year_months": {"tr": "12 ay üzerinden", "en": "over 12 months"},
    "calc.how": {"tr": "Bu sayı nasıl çıkıyor?", "en": "How is this number calculated?"},
    "calc.input_price": {"tr": "Girdi fiyatı", "en": "Input price"},
    "calc.output_price": {"tr": "Çıktı fiyatı", "en": "Output price"},
    "calc.rate": {"tr": "Kur", "en": "Rate"},
    "calc.rate_note": {
        "tr": "kur değişimi USD maliyetini değiştirmez",
        "en": "exchange-rate changes do not affect the USD cost",
    },
    "calc.no_cache": {
        "tr": "Önbellek (cache) ve toplu (batch) indirimleri hesaba katılmamıştır.",
        "en": "Cache and batch discounts are not included.",
    },
    "calc.no_quality": {
        "tr": "Kalite, gecikme ve bağlam penceresi karşılaştırılmamıştır; aynı kalite varsayımı yapılmamaktadır.",
        "en": "Quality, latency and context window are not compared; equal quality is not assumed.",
    },
    "calc.invalid_tokens": {"tr": "Geçerli bir token sayısı girin.", "en": "Enter a valid token count."},

    # --- ek: karsilastir ---
    "cmp.search_hint": {"tr": "Model ara", "en": "Search models"},
    "cmp.models_heading": {"tr": "Karşılaştırılacak modeller", "en": "Models to compare"},
    "cmp.result": {"tr": "Sonuç", "en": "Result"},
    "cmp.tr_badge": {"tr": "Türkçe içerik varsayımı", "en": "Turkish content assumption"},
    "cmp.en_badge": {"tr": "İngilizce · çarpan yok", "en": "English · no multiplier"},
    "cmp.text_lang": {"tr": "Metin dili", "en": "Text language"},
    "cmp.lang_help": {
        "tr": "Türkçe metin aynı içerik için daha fazla token harcar; çarpan her iki modele uygulanır.",
        "en": "Turkish text uses more tokens for the same content; the multiplier applies to both models.",
    },

    # --- ek: token sayaci ---
    "tok.text": {"tr": "Metin", "en": "Text"},
    "tok.result": {"tr": "Sonuç", "en": "Result"},
    "tok.cost_by_model": {"tr": "Modele göre maliyet", "en": "Cost by model"},
    "tok.english": {"tr": "İngilizce", "en": "English"},
    "tok.turkish": {"tr": "Türkçe", "en": "Turkish"},
    "tok.multiplier": {"tr": "Türkçe çarpanı", "en": "Turkish multiplier"},
    "tok.clear": {"tr": "Temizle", "en": "Clear"},

    # --- ek: gpu ---
    "gpu.sort": {"tr": "Sırala", "en": "Sort"},
    "gpu.sort.vram": {"tr": "VRAM: yüksek → düşük", "en": "VRAM: high → low"},
    "gpu.sort.price": {"tr": "Fiyat: düşük → yüksek", "en": "Price: low → high"},
    "gpu.on_demand": {"tr": "On-demand", "en": "On-demand"},
    "gpu.spot": {"tr": "Spot", "en": "Spot"},
    "gpu.reserved": {"tr": "Rezerve", "en": "Reserved"},
    "gpu.community": {"tr": "Topluluk", "en": "Community"},
    "gpu.filters": {"tr": "Filtreler", "en": "Filters"},
    "gpu.empty": {"tr": "Bu filtrelerle GPU bulunamadı.", "en": "No GPUs match these filters."},
    "gpu.how_to_read": {"tr": "Bu veriyi nasıl okumalı?", "en": "How to read this data?"},
    "gpu.source_freshness": {"tr": "Kaynak ve tazelik", "en": "Source and freshness"},

    # --- ek: uyari ---
    "alert.consent": {"tr": "Aydınlatma metnini okudum, onaylıyorum", "en": "I have read and accept the privacy notice"},
    "alert.consent_link": {"tr": "Aydınlatma metni", "en": "Privacy notice"},
    "alert.already": {"tr": "Bu kayıt zaten var.", "en": "This alert already exists."},
    "alert.optional": {"tr": "isteğe bağlı", "en": "optional"},
    "alert.target": {"tr": "Hangi model?", "en": "Which model?"},
    "alert.all_models": {"tr": "Tüm modeller", "en": "All models"},
}


def t(key: str, lang: str = DEFAULT_LANG) -> str:
    entry = STRINGS.get(key, {})
    return entry.get(lang) or entry.get(DEFAULT_LANG) or key
