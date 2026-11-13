"""Turnstile entegrasyon testleri (rapor 5. tur P0-5).

Widget mevcut (site key 0x4AAAAAAF_TxkQHNciYw5a6); server-side siteverify
eklendi. Bu testler sozlesmeyi kilitler.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FN = ROOT / "functions"
TPL = ROOT / "backend" / "app" / "web" / "templates" / "uyari.html"


def read(p):
    return p.read_text(encoding="utf-8")


def test_verify_helper_exists():
    s = read(FN / "_lib" / "turnstile.js")
    assert "siteverify" in s
    assert "TURNSTILE_SECRET" in s, "secret env'den okunmali"
    assert "fail-closed" in s or "ok: false" in s


def test_secret_never_in_client():
    """Secret key istemciye ASLA gitmemeli.

    NOT: TURNSTILE_SECRET adi Jinja YORUMUNDA gecebilir (dokumantasyon amacli);
    onemli olan secret DEGERININ ve ortam degiskeni okumasinin template'e
    girmemesi.
    """
    tpl = read(TPL)
    # secret degeri (0x4A... sonrasi farkli) asla gorunmemeli
    assert "0x4AAAAAAF_TxoflLkNLIhL3QYUqXM3l4B4" not in tpl, "secret hardcoded!"
    # ortam degiskeni okuma istemcide olmamali
    assert "env.TURNSTILE_SECRET" not in tpl
    assert "os.getenv(\"TURNSTILE_SECRET\")" not in tpl
    # widget yalnizca site key kullanir
    assert 'data-sitekey="' in tpl


def test_form_has_widget_and_script():
    """Widget formda; site key CONTEXT degiskeninden gelir (hardcode degil)."""
    tpl = read(TPL)
    assert 'class="cf-turnstile"' in tpl
    assert 'data-sitekey="{{ turnstile_site_key }}"' in tpl
    assert "challenges.cloudflare.com/turnstile/v0/api.js" in tpl


def test_site_key_in_context_with_correct_default():
    s = read(ROOT / "backend" / "app" / "web" / "render.py")
    assert "turnstile_site_key" in s
    assert "0x4AAAAAAF_TxkQHNciYw5a6" in s, "varsayilan site key yok"


def test_api_verifies_before_writing():
    s = read(FN / "api" / "uyari.js")
    assert "verifyTurnstile" in s
    assert 'form.get("cf-turnstile-response")' in s
    # dogrulama DB yazimindan ONCE olmali
    i_verify = s.index("await verifyTurnstile")
    i_insert = s.index("INSERT INTO price_alerts")
    assert i_verify < i_insert, "siteverify DB yazimindan sonra"


def test_csp_allows_challenges():
    s = read(ROOT / "scripts" / "export_static.py")
    assert "https://challenges.cloudflare.com" in s
    assert "frame-src https://challenges.cloudflare.com" in s
