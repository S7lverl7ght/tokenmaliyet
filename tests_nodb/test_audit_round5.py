"""5. tur denetim raporu duzeltmelerinin testleri.

Rapor: KAPSAMLI_DENETIM_VE_GELISTIRME_RAPORU.md (13.11.2026)
Kapatilan P0/P1 bulgular:
  - Stored XSS (onayla/iptal/uyari/bildir)
  - Token sayaci bozuk model-options
  - Istemci tarafli hesap motoru eksikligi
  - _headers MIME cakismasi
  - 50 subrequest siniri (Resend batch)
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FN = ROOT / "functions"


def read(p):
    return p.read_text(encoding="utf-8")


# ---------- P0-1: Stored XSS ----------

def test_escape_helper_exists():
    s = read(FN / "_lib" / "sanitize.js")
    assert "export function escapeHtml" in s
    assert "&amp;" in s and "&lt;" in s and "&gt;" in s and "&quot;" in s
    assert "headerSafe" in s, "e-posta baslik enjeksiyonu korumasi yok"


def test_confirm_page_escapes_label():
    s = read(FN / "api" / "onayla.js")
    assert 'import { escapeHtml }' in s
    assert "escapeHtml(row.target_label)" in s
    # ham kullanim kalmamali
    assert '"<strong>" + row.target_label' not in s


def test_unsubscribe_page_escapes_label():
    s = read(FN / "api" / "iptal.js")
    assert "escapeHtml(row.target_label)" in s
    assert '"<strong>" + row.target_label' not in s


def test_email_html_escapes_user_input():
    u = read(FN / "api" / "uyari.js")
    b = read(FN / "api" / "bildir.js")
    assert "escapeHtml(targetLabel)" in u
    assert "escapeHtml(label)" in b
    # baslikta kontrol karakteri temizligi
    assert "headerSafe(label" in b


# ---------- P0-2: token sayaci ----------

def test_export_writes_real_model_options():
    s = read(ROOT / "scripts" / "export_static.py")
    assert '/api/v1/model-options' in s
    assert "resp_options.content" in s, "gercek JSON yazilmiyor"
    assert '"error":"Statik yayinda API kapali"' not in s, "eski hata stub'i kalmis"


def test_token_counter_guards_non_array():
    s = read(ROOT / "backend" / "app" / "web" / "templates" / "token_sayaci.html")
    assert "Array.isArray(list)" in s, "dizi olmayan yanit icin koruma yok"


# ---------- P0-3: istemci hesap motoru ----------

def test_calculator_has_client_engine():
    s = read(ROOT / "backend" / "app" / "web" / "templates" / "calculator.html")
    assert "recalcClient" in s
    assert "__MODEL_OPTIONS__" in s
    assert 'data-role="from-usd"' in s and 'data-role="to-usd"' in s
    assert 'data-role="pct"' in s
    # onbellek ve dil carpani hesaba katilmali
    assert "cacheShare" in s and "trMult" in s


def test_compare_has_client_engine():
    s = read(ROOT / "backend" / "app" / "web" / "templates" / "compare.html")
    assert "__MODEL_OPTIONS__" in s
    assert "data-card=" in s
    assert 'data-role="card-usd"' in s


def test_options_include_cache_price():
    s = read(ROOT / "backend" / "app" / "web" / "routes.py")
    assert '"cache_price": pcache' in s


# ---------- P0-4: MIME ----------

def test_headers_have_per_endpoint_mime():
    s = read(ROOT / "scripts" / "export_static.py")
    assert '"/api/onayla",' in s and 'text/html; charset=utf-8' in s
    assert '"/api/iptal",' in s
    assert '"/api/v1/*",' in s
    # global /api/* json kalmamali
    assert '"/api/*",' not in s


# ---------- P1: subrequest ----------

def test_batch_mail_used():
    m = read(FN / "_lib" / "mail.js")
    b = read(FN / "api" / "bildir.js")
    assert "sendMailBatch" in m
    assert "/batch" in m, "Resend batch ucu kullanilmiyor"
    assert "sendMailBatch(env, slice)" in b
    assert "await sendMail(" not in b, "tek tek gonderim kalmis"
    assert "const CHUNK = 100" in b


# ---------- P1-4: anlik arama ----------

def test_models_index_generated():
    s = read(ROOT / "scripts" / "export_static.py")
    assert "models-index.json" in s
    assert '"n": r.name' in s


def test_instant_search_panel():
    s = read(ROOT / "backend" / "app" / "web" / "templates" / "prices.html")
    assert 'id="instant-search"' in s
    assert 'id="live-q"' in s
    assert "models-index.json" in s
    assert "toLocaleLowerCase" in s, "Turkce normalizasyonu yok"


# ---------- P1-5: affiliate ----------

def test_affiliate_is_config_driven():
    s = read(ROOT / "backend" / "app" / "web" / "affiliate.py")
    assert "AFFILIATE_" in s
    assert "def with_affiliate" in s
    # uydurma kod olmamali: kod yoksa URL aynen doner
    assert "if not param or not url:" in s


def test_gpu_uses_affiliate_helper():
    s = read(ROOT / "backend" / "app" / "web" / "routes.py")
    assert "with_affiliate(gp.pricing_url" in s


# ---------- P2-1: danismanlik ----------

def test_consulting_page_exists():
    p = ROOT / "backend" / "app" / "web" / "templates" / "danismanlik.html"
    assert p.exists()
    s = p.read_text(encoding="utf-8")
    assert "caching" in s.lower()
    assert "hesaplayici" in s, "hesaplayiciya baglanti yok"


def test_consulting_route_and_nav():
    r = read(ROOT / "backend" / "app" / "web" / "routes.py")
    b = read(ROOT / "backend" / "app" / "web" / "templates" / "base.html")
    assert '"/danismanlik"' in r
    assert 'href="/danismanlik"' in b
