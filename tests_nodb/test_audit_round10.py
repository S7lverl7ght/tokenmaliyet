"""8. tur denetim raporundaki hatalarin regresyon testleri.

Kaynak: AI-Maliyet-Cikti/8TUR_DENETIM_VE_GELISTIRME_RAPORU.md
Dort hata da ONCE kodda dogrulandi, sonra duzeltildi, simdi kilitlendi.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

DIST = ROOT / "dist"
EXPORT = ROOT / "scripts" / "export_static.py"
TPL = ROOT / "backend" / "app" / "web" / "templates"


# ---------------------------------------------------------------- HATA-1
def test_headers_cover_newsletter_endpoints():
    """_headers blogu /api/bulten* uclarini icermeli."""
    src = EXPORT.read_text(encoding="utf-8")
    for ep in ("/api/bulten", "/api/bulten-onay", "/api/bulten-iptal", "/api/bulten-gonder"):
        assert f'"{ep}"' in src, f"_headers icin {ep} tanimsiz"


@pytest.mark.skipif(not DIST.exists(), reason="dist/ yok")
def test_built_headers_file_has_newsletter():
    hdr = (DIST / "_headers").read_text(encoding="utf-8")
    for ep in ("/api/bulten", "/api/bulten-onay", "/api/bulten-iptal", "/api/bulten-gonder"):
        assert ep in hdr, f"{ep} _headers icinde yok"
    # HTML donen onay/iptal uclari text/html olmali
    idx = hdr.index("/api/bulten-onay")
    assert "text/html" in hdr[idx:idx + 120]


# ---------------------------------------------------------------- HATA-2
def test_media_cost_returns_divisor():
    """Sunucu hesabi bolen degerini de dondurmeli (istemci ayni sayiyi kullanacak)."""
    from app.web import media_cost as mc

    rows = mc.compare("tts", 10000)
    assert rows
    for r in rows:
        assert "divisor" in r, "divisor yok"
        assert r["divisor"] > 0
        # Sunucu sonucu, bolen tanimina gore dogru olmali
        assert abs((r["quantity"] / r["divisor"]) * r["usd_per_unit"] - r["usd"]) < 1e-9


@pytest.mark.skipif(not DIST.exists(), reason="dist/ yok")
def test_media_table_has_client_hooks():
    """Ses maliyeti tablosu istemci motorunun okudugu data-* ozniteliklerini tasimali."""
    for rel in ("hesaplayici/ses-maliyeti", "en/hesaplayici/ses-maliyeti"):
        p = DIST / rel / "index.html"
        if not p.exists():
            continue
        html = p.read_text(encoding="utf-8", errors="ignore")
        assert "data-unit-price=" in html, f"{rel}: data-unit-price yok"
        assert "data-divisor=" in html, f"{rel}: data-divisor yok"
        assert "cell-total-usd" in html, f"{rel}: .cell-total-usd yok"
        assert "cell-total-try" in html, f"{rel}: .cell-total-try yok"


def test_media_template_has_client_engine():
    tpl = (TPL / "ses_maliyeti.html").read_text(encoding="utf-8")
    assert "{% block scripts %}" in tpl, "istemci motoru blogu yok"
    assert "dataset.unitPrice" in tpl or "dataset.unitprice" in tpl.lower()
    assert "dataset.divisor" in tpl
    # JS kapaliysa form klasik GET olarak calismali (metod korunmali)
    assert 'method="get"' in tpl


# ---------------------------------------------------------------- HATA-3
def test_media_affiliate_is_wired(monkeypatch):
    """AFFILIATE_<SAGLAYICI> tanimliysa medya kaynagina parametre eklenmeli."""
    from app.web import media_cost as mc

    monkeypatch.delenv("AFFILIATE_ELEVENLABS", raising=False)
    plain = [r for r in mc.compare("tts", 10000) if r["provider"] == "ElevenLabs"]
    if plain:
        assert "ref=" not in plain[0]["source"]
        assert plain[0]["affiliate"] is False

    monkeypatch.setenv("AFFILIATE_ELEVENLABS", "ref=test123")
    tagged = [r for r in mc.compare("tts", 10000) if r["provider"] == "ElevenLabs"]
    if tagged:
        assert "ref=test123" in tagged[0]["source"]
        assert tagged[0]["affiliate"] is True


def test_affiliate_absent_means_plain_url(monkeypatch):
    """Kod yoksa URL DEGISMEMELI (uydurma kod yazilmaz)."""
    from app.web import media_cost as mc

    monkeypatch.delenv("AFFILIATE_OPENAI", raising=False)
    for r in mc.compare("tts", 10000):
        if r["provider"] == "OpenAI":
            assert "?" not in r["source"] or "ref=" not in r["source"]


@pytest.mark.skipif(not DIST.exists(), reason="dist/ yok")
def test_affiliate_disclosure_present_when_enabled(monkeypatch):
    """Ortaklik baglantisi kullaniliyorsa sayfada aciklama olmali (seffaflik)."""
    tpl = (TPL / "ses_maliyeti.html").read_text(encoding="utf-8")
    assert "r.affiliate" in tpl, "ortaklik etiketi/sartli rel yok"


# ---------------------------------------------------------------- HATA-4
def test_newsletter_send_endpoint_exists():
    fn = ROOT / "functions" / "api" / "bulten-gonder.js"
    assert fn.exists(), "bulten-gonder.js yok"
    body = fn.read_text(encoding="utf-8")
    # Yalnizca cift onayli ve cikmamis aboneler
    assert "confirmed = 1" in body
    assert "unsubscribed_at IS NULL" in body
    # Kimlik dogrulama
    assert "BILDIR_SECRET" in body
    assert "timingSafeEqual" in body
    # Her e-postada cikis baglantisi
    assert "bulten-iptal?t=" in body
    # Toplu gonderim (alt istek siniri)
    assert "sendMailBatch" in body


def test_newsletter_content_script_exists():
    p = ROOT / "scripts" / "bulten_icerik.py"
    assert p.exists(), "bulten_icerik.py yok"
    src = p.read_text(encoding="utf-8")
    assert "price_history" in src
    assert "bulten_payload.json" in src


def test_weekly_newsletter_workflow():
    wf = ROOT / ".github" / "workflows" / "bulten.yml"
    assert wf.exists(), "haftalik bulten workflow'u yok"
    src = wf.read_text(encoding="utf-8")
    # Haftalik zamanlama (pazartesi)
    assert "cron:" in src and "* * 1" in src
    # Elle tetiklendiginde guvenli varsayilan: gonder ME
    assert "dry_run" in src
    assert "bulten-gonder" in src


def test_newsletter_send_disallowed_in_robots():
    src = (ROOT / "backend" / "app" / "web" / "routes.py").read_text(encoding="utf-8")
    assert "Disallow: /api/bulten-gonder" in src
