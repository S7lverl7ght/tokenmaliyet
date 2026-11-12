"""Fiyat uyarisi cift onay + iptal akisi sozlesme testleri."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FN = ROOT / "functions"


def read(p):
    return p.read_text(encoding="utf-8")


def test_signup_creates_tokens():
    src = read(FN / "api" / "uyari.js")
    assert "confirm_token" in src and "unsubscribe_token" in src
    assert "confirmed" in src and "0," in src, "kayit onaysiz baslamali"


def test_signup_sends_confirmation_mail():
    src = read(FN / "api" / "uyari.js")
    assert "sendMail" in src
    assert "/api/onayla?t=" in src, "onay linki yok"
    assert "/api/iptal?t=" in src, "iptal linki yok"
    assert "cift onay" in src.lower() or "onaylamazsaniz" in src.lower()


def test_confirm_endpoint():
    src = read(FN / "api" / "onayla.js")
    assert "confirm_token" in src
    assert "confirmed = 1" in src
    assert "confirmed_at" in src
    assert "noindex" in src, "onay sayfasi indekslenmemeli"
    assert "[a-f0-9]{16,64}" in src, "token formati dogrulanmali"


def test_unsubscribe_endpoint():
    src = read(FN / "api" / "iptal.js")
    assert "unsubscribe_token" in src
    assert "unsubscribed_at" in src
    assert "confirmed = 0" in src


def test_notify_requires_secret():
    src = read(FN / "api" / "bildir.js")
    assert "BILDIR_SECRET" in src
    assert "401" in src, "yetkisiz istek reddedilmeli"
    assert "x-bildir-secret" in src


def test_notify_respects_threshold_and_direction():
    src = read(FN / "api" / "bildir.js")
    assert "threshold_pct" in src
    assert "direction" in src
    assert '"down"' in src and '"up"' in src
    assert "confirmed = 1" in src and "unsubscribed_at IS NULL" in src


def test_mail_helper_is_optional():
    src = read(FN / "_lib" / "mail.js")
    assert "RESEND_API_KEY" in src
    assert "not_configured" in src, "anahtar yoksa sessiz donmeli"


def test_changes_script_exists():
    p = ROOT / "scripts" / "alert_changes.py"
    assert p.exists()
    src = read(p)
    assert "NOTIFY_DIMENSIONS" in src
    assert "alert_changes.json" in src
