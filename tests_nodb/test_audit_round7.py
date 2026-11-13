"""7. tur denetim raporu regresyon testleri (13.11.2026).

Kapatilan bulgular:
  HATA-1: _headers icinde /api/iletisim yoktu
  HATA-2: "danismanlik" konusu iletisim formunda yoktu
  HATA-3: gecici test dosyalari depoda kaliyordu
  UX-1  : basarili gonderimde form yerine tesekkur karti
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FN = ROOT / "functions"


def read(p):
    return p.read_text(encoding="utf-8")


# ---------- HATA-1 ----------

def test_headers_include_contact_api():
    s = read(ROOT / "scripts" / "export_static.py")
    assert '"/api/iletisim"' in s, "_headers icin /api/iletisim tanimsiz"


def test_headers_contact_is_json_noindex():
    s = read(ROOT / "scripts" / "export_static.py")
    i = s.index('"/api/iletisim"')
    block = s[i:i + 200]
    assert "application/json" in block
    assert "noindex" in block


# ---------- HATA-2 ----------

def test_consulting_topic_in_routes():
    s = read(ROOT / "backend" / "app" / "web" / "routes.py")
    i = s.index("CONTACT_TOPICS")
    assert "danismanlik" in s[i:i + 400]


def test_consulting_topic_in_function():
    s = read(FN / "api" / "iletisim.js")
    i = s.index("const TOPICS")
    assert "danismanlik" in s[i:i + 300]


def test_consulting_page_links_with_topic():
    s = read(ROOT / "backend" / "app" / "web" / "templates" / "danismanlik.html")
    assert "/iletisim?topic=danismanlik" in s


def test_contact_accepts_topic_query_param():
    s = read(ROOT / "backend" / "app" / "web" / "routes.py")
    assert 'query_params.get("topic")' in s


# ---------- HATA-3 ----------

def test_gitignore_covers_test_artifacts():
    g = read(ROOT / ".gitignore")
    assert "_*.png" in g, "ekran goruntuleri ignore edilmiyor"
    assert "_*.json" in g


# ---------- UX-1 ----------

def test_thank_you_card_exists():
    s = read(ROOT / "backend" / "app" / "web" / "templates" / "iletisim.html")
    assert 'id="tesekkur"' in s
    assert "form.hidden = true" in s, "basarida form gizlenmiyor"
    assert 'id="yeniMesaj"' in s, "yeniden acma butonu yok"
