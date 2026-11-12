"""Guvenlik testleri - inceleme raporu (12.11.2026) guvenlik bolumu."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app

XSS = "<script>alert(1)</script>"
XSS_ATTR = '" onmouseover="alert(1)'


@pytest.fixture(scope="module")
def client(seeded_data):
    return TestClient(app)


def test_calculator_escapes_share_params(client):
    """Paylasim parametreleri HTML olarak kacislanmali.

    Jinja2 tirnak ve kucuk-isaretleri kacislar (&#34; &lt;). Bu yuzden kontrol
    "ham payload ciktiya sizmadi mi" uzerinden yapilir.
    """
    r = client.get("/hesaplayici", params={"from": XSS, "to": XSS_ATTR})
    assert r.status_code == 200
    body = r.text
    # ham script etiketi hicbir yerde olmamali
    assert "<script>alert(1)</script>" not in body
    # tirnak kacislanmis olmali: &quot; veya &#34;
    assert "&#34;" in body or "&quot;" in body


def test_prices_escapes_search_query(client):
    r = client.get("/fiyatlar", params={"q": XSS})
    assert r.status_code == 200
    assert "<script>alert(1)</script>" not in r.text


def test_compare_escapes_model_params(client):
    r = client.get("/karsilastir", params=[("models", XSS), ("models", XSS_ATTR)])
    assert r.status_code == 200
    assert "<script>alert(1)</script>" not in r.text


def test_negative_tokens_rejected(client):
    r = client.get("/hesaplayici", params={"in": "-5000", "out": "100"})
    assert r.status_code == 200
    assert "aria-invalid" in r.text or "Negatif" in r.text


def test_huge_tokens_rejected(client):
    r = client.get("/hesaplayici", params={"in": "999999999999999999", "out": "1"})
    assert r.status_code == 200
    assert "aria-invalid" in r.text or "Cok buyuk" in r.text or "büyük" in r.text


def test_non_numeric_tokens_rejected(client):
    r = client.get("/hesaplayici", params={"in": "abc", "out": "xyz"})
    assert r.status_code == 200
    assert "aria-invalid" in r.text


def test_security_headers_present(client):
    h = client.get("/fiyatlar").headers
    assert h.get("x-content-type-options") == "nosniff"
    assert h.get("x-frame-options") in ("SAMEORIGIN", "DENY")
    assert "content-security-policy" in {k.lower() for k in h}
    assert "frame-ancestors" in h.get("content-security-policy", "")


def test_external_links_have_noopener(client):
    body = client.get("/fiyatlar").text
    import re
    for m in re.finditer(r'<a[^>]+target="_blank"[^>]*>', body):
        tag = m.group(0)
        assert "noopener" in tag, f"target=_blank without noopener: {tag[:90]}"


def test_admin_requires_token(client, monkeypatch):
    monkeypatch.delenv("ADMIN_TOKEN", raising=False)
    r = client.get("/admin/kuyruk", follow_redirects=False)
    assert r.status_code in (403, 303)
