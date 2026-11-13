"""Iletisim formu testleri (kullanici istegi, 13.11.2026).

Gereksinim:
  - iletisim@tokenmaliyet.com adresi KALDIRILDI (mailbox yok)
  - Yerlesik iletisim formu: kullanici mesaj yazar
  - Mesaj sahibine (omerktn55@gmail.com) e-posta olarak gider
  - Kullanicinin kendi adresi Reply-To olur
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TPL = ROOT / "backend" / "app" / "web" / "templates"


def read(p):
    return p.read_text(encoding="utf-8")


def test_contact_page_has_form():
    t = read(TPL / "iletisim.html")
    assert 'id="iletisimForm"' in t
    assert 'data-api="/api/iletisim"' in t
    for field in ("name", "email", "topic", "message"):
        assert f'name="{field}"' in t, f"{field} alani yok"


def test_contact_form_requires_user_email():
    t = read(TPL / "iletisim.html")
    assert 'id="email"' in t and 'type="email"' in t and "required" in t


def test_contact_form_has_bot_protection():
    t = read(TPL / "iletisim.html")
    assert "cf-turnstile" in t, "Turnstile yok"
    assert 'name="website"' in t, "bal kupu yok"


def test_old_contact_email_removed():
    """iletisim@tokenmaliyet.com artik kod tabaninda olmamali."""
    for rel in ("templates/iletisim.html", "routes.py"):
        p = ROOT / "backend" / "app" / "web" / rel
        assert "iletisim@tokenmaliyet.com" not in read(p), f"{rel} hala eski adresi iceriyor"


def test_function_sends_to_owner_with_replyto():
    s = read(ROOT / "functions" / "api" / "iletisim.js")
    assert "omerktn55@gmail.com" in s, "sahip adresi yok"
    assert "replyTo: email" in s, "Reply-To kullanici adresi degil"
    assert "verifyTurnstile" in s, "bot korumasi yok"


def test_function_stores_before_mail():
    """Mail basarisiz olsa bile mesaj D1'de kalmali."""
    s = read(ROOT / "functions" / "api" / "iletisim.js")
    i_store = s.index("INSERT INTO contact_messages")
    i_mail = s.index("await sendMail(")
    assert i_store < i_mail, "once D1'e yazilmali"


def test_mail_lib_supports_reply_to():
    s = read(ROOT / "functions" / "_lib" / "mail.js")
    assert "replyTo" in s and "reply_to" in s


def test_contact_table_schema():
    s = read(ROOT / "db" / "contact.sql")
    assert "contact_messages" in s
    assert "mail_sent" in s
