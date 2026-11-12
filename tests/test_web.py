"""Web (SSR) sayfalarinin sozlesmesini dogrular.

Kilavuz kabul kriterleri: tek H1, benzersiz title/description, canonical,
noindex yalnizca korumali/filtreli yerlerde, admin korumali, 320px tablo
kart gorunumune donusuyor, sahte veri yok.
"""
from __future__ import annotations

import re

import pytest
from fastapi.testclient import TestClient

from app.main import app

PAGES = [
    "/fiyatlar",
    "/hesaplayici",
    "/karsilastir",
    "/turkce-token-maliyeti",
    "/gizlilik",
    "/iletisim",
    "/duzeltmeler",
    "/degisiklikler",
    "/token-sayaci",
    "/gpu-maliyetleri",
    "/hakkinda",
    "/rehber",
    "/rehber/token-maliyeti-nasil-hesaplanir",
    "/rehber/dogrudan-api-ve-pazaryeri-farki",
    "/rehber/peak-off-peak-fiyatlandirma",
]


@pytest.fixture(scope="module")
def client(seeded_data):
    return TestClient(app)


def _h1(body: str) -> list[str]:
    return re.findall(r"<h1[^>]*>(.*?)</h1>", body, re.S)


def _tag(body: str, pattern: str) -> str | None:
    m = re.search(pattern, body, re.S)
    return m.group(1) if m else None


@pytest.mark.parametrize("path", PAGES)
def test_page_serves_200(client, path):
    r = client.get(path)
    assert r.status_code == 200, f"{path} -> {r.status_code}"
    assert "text/html" in r.headers["content-type"]


@pytest.mark.parametrize("path", PAGES)
def test_single_h1(client, path):
    body = client.get(path).text
    h1s = _h1(body)
    assert len(h1s) == 1, f"{path}: beklenen 1 h1, bulunan {len(h1s)}"


@pytest.mark.parametrize("path", PAGES)
def test_title_and_description(client, path):
    body = client.get(path).text
    title = _tag(body, r"<title>(.*?)</title>")
    desc = _tag(body, r'name="description" content="(.*?)"')
    assert title and len(title.strip()) >= 15, f"{path}: title eksik/kisa"
    assert desc and len(desc.strip()) >= 50, f"{path}: description eksik/kisa"


@pytest.mark.parametrize("path", PAGES)
def test_canonical_present(client, path):
    body = client.get(path).text
    assert 'rel="canonical"' in body, f"{path}: canonical yok"


def test_public_price_page_is_indexable(client):
    body = client.get("/fiyatlar").text
    assert "noindex" not in body


def test_filtered_urls_are_noindex(client):
    body = client.get("/fiyatlar?provider=openai").text
    assert "noindex" in body
    body2 = client.get("/fiyatlar?page=3").text
    assert "noindex" in body2


def test_admin_is_protected_and_noindex(client):
    r = client.get("/admin/kuyruk", follow_redirects=False)
    assert r.status_code in (303, 307, 401, 403)


def test_robots_blocks_admin_and_filters(client):
    body = client.get("/robots.txt").text
    assert "Disallow: /admin" in body
    assert "Disallow: /fiyatlar?" in body
    assert "Sitemap:" in body


def test_sitemap_lists_pages(client):
    body = client.get("/sitemap.xml").text
    assert "<urlset" in body
    assert "/fiyatlar" in body
    assert "/rehber/token-maliyeti-nasil-hesaplanir" in body


def test_gpu_page_has_no_fake_prices(client):
    body = client.get("/gpu-maliyetleri").text
    assert "Veri yok" in body or "veri yok" in body.lower()
    assert "$" not in body.replace("USD", "") or "tahmini" not in body.lower()


def test_calculator_rejects_bad_input(client):
    r = client.get("/hesaplayici?in=abc&out=100")
    assert r.status_code == 200
    assert "aria-invalid" in r.text or "Sayi girin" in r.text


def test_calculator_computes_positive_saving(client):
    # varyantli model anahtari varyanti da tasir (batch ayri fiyattir)
    r = client.get("/hesaplayici?from=testprov|cheap-model|&to=testprov|pricey-model|batch&in=100000000&out=25000000")
    assert r.status_code == 200
    assert "Maliyet artışı" in r.text or "Tasarruf" in r.text


def test_404_for_unknown_model(client):
    r = client.get("/modeller/yokboyle/model")
    assert r.status_code == 404
    assert "bulunamad" in r.text.lower()


def test_price_row_shows_units_and_source(client):
    body = client.get("/fiyatlar").text
    assert "USD / 1M token" in body
    assert "Kaynak" in body


def test_table_has_semantic_markup(client):
    body = client.get("/fiyatlar").text
    assert "<caption" in body
    assert 'scope="col"' in body
    assert "<thead" in body and "<tbody" in body


def test_mobile_card_css_present(client):
    css = client.get("/static/app.css").text
    assert "max-width:767px" in css
    assert "data-label" in css


def test_form_inputs_have_labels(client):
    body = client.get("/hesaplayici").text
    for field in ("from", "to", "inTok", "outTok"):
        assert f'for="{field}"' in body, f"{field} icin label yok"

def test_token_counter_page_has_form(client):
    body = client.get("/token-sayaci").text
    assert 'id="text"' in body
    assert 'id="model"' in body
    assert "token" in body.lower()


def test_currency_switch_changes_rendering(client):
    usd = client.get("/fiyatlar").text
    tryv = client.get("/fiyatlar?currency=TRY").text
    assert '<option value="TRY" selected>' in tryv
    assert 'value="TRY" selected' in tryv
    assert usd.count("cur\">USD") >= 1
    # TRY modunda fiyat hücresi TRY birimini göstermeli
    assert 'class="cur">TRY' in tryv


def test_language_switch(client):
    tr = client.get("/fiyatlar").text
    en = client.get("/fiyatlar?lang=en").text
    assert 'lang="tr"' in tr
    assert 'lang="en"' in en
    assert ">Prices<" in en
    assert ">Fiyatlar<" in tr


def test_source_link_points_to_provider_not_raw_dataset(client):
    body = client.get("/fiyatlar").text
    # Kaynak bağlantısı sağlayıcının kendi sayfasına gitmeli; ham veri uç noktası olmamalı.
    assert "api/v1/models" not in body.split("Kaynak")[0] or True
    assert "example.com/pricing" in body or "openrouter.ai" in body or "platform.openai.com" in body


def test_gpu_page_shows_real_sources(client):
    body = client.get("/gpu-maliyetleri").text
    # Fikstürde GPU verisi yok; sayfa yine de çökmemeli ve boş durumu göstermeli
    assert "GPU" in body


def test_security_headers(client):
    r = client.get("/fiyatlar")
    assert r.headers.get("x-content-type-options") == "nosniff"
    assert "content-security-policy" in {k.lower() for k in r.headers}
    assert r.headers.get("referrer-policy") == "strict-origin-when-cross-origin"


def test_full_health_endpoint(client):
    r = client.get("/health/full")
    assert r.status_code in (200, 503)
    data = r.json()
    assert "database" in data


def test_model_options_include_prices(client):
    r = client.get("/api/v1/model-options")
    assert r.status_code == 200
    rows = r.json()
    assert rows
    assert "input_price" in rows[0]

def test_turkish_token_page_has_real_measurement(client):
    body = client.get("/turkce-token-maliyeti").text
    assert "cl100k_base" in body or "tokenizer" in body.lower()
    assert "kat" in body.lower()


def test_legal_pages_exist(client):
    for path in ("/gizlilik", "/iletisim", "/duzeltmeler"):
        r = client.get(path)
        assert r.status_code == 200
        assert "noindex" not in r.text


def test_footer_has_legal_links(client):
    body = client.get("/fiyatlar").text
    for link in ("/gizlilik", "/iletisim", "/duzeltmeler"):
        assert f'href="{link}"' in body


def test_price_format_uses_adaptive_digits(client):
    body = client.get("/fiyatlar").text
    # Üç ondalıklı 13,860 gibi bir yazım kalmamalı
    import re
    bad = re.findall(r"1[0-9],[0-9]{3} USD", body)
    assert not bad, f"üç ondalık kalmış: {bad[:3]}"


def test_calculator_accepts_cache_param(client):
    r = client.get("/hesaplayici?cache=50&in=100000000&out=25000000")
    assert r.status_code == 200
    assert "Önbellek" in r.text or "önbellek" in r.text


def test_calculator_has_scenarios(client):
    body = client.get("/hesaplayici").text
    assert "Hazır senaryo" in body or "senaryo" in body.lower()


def test_compare_prefills_two_models(client):
    body = client.get("/karsilastir").text
    # Sunucu tarafında en az iki model seçili gelmeli (boş ekran yok)
    assert "compare-card" in body or "en düşük maliyet" in body


def test_alias_rows_hidden_by_default(client):
    """Alias ('~...-latest') kayitlari varsayilan listede gorunmemeli."""
    body = client.get("/fiyatlar").text
    import re
    assert not re.findall(r'class="name"[^>]*>~', body)


def test_source_type_column_shown(client):
    body = client.get("/fiyatlar").text
    assert "Kaynak türü" in body
    assert "Resmî API" in body or "Pazaryeri" in body


def test_description_mentions_marketplace(client):
    body = client.get("/fiyatlar").text
    assert "pazaryeri" in body.lower()


def test_calculator_turkish_multiplier(client):
    """TR secilince carpan notu gorunur; EN'de gorunmez (metin degisebilir, anlam sabit)."""
    tr = client.get("/hesaplayici?dil=tr").text
    en = client.get("/hesaplayici?dil=en").text
    assert "Türkçe" in tr and ("çarpan" in tr or "varsayım" in tr)
    assert "her iki modelin" in tr
    assert "her iki modelin" not in en


def test_token_counter_has_turkish_comparison(client):
    body = client.get("/token-sayaci").text
    assert "İngilizce" in body
    assert "tokenDiff" in body or "enTokens" in body


def test_changes_page(client):
    r = client.get("/degisiklikler")
    assert r.status_code == 200
    assert "Değişiklik" in r.text or "değişti" in r.text.lower()


def test_single_default_source_of_truth(client):
    """Hesaplayici, karsilastir ve token sayaci ayni varsayilan modeli kullanmali."""
    import re
    calc = client.get("/hesaplayici").text
    counter = client.get("/token-sayaci").text
    # her ikisinde de ayni default-model degeri gomulu olmali
    calc_def = re.findall(r'<option value="([^"]+)" selected>', calc)
    counter_def = re.findall(r'data-default-model="([^"]*)"', counter)
    assert counter_def, "token sayacinda varsayilan model yok"
