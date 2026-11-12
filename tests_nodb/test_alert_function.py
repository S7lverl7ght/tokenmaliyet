"""Fiyat uyarisi fonksiyonu sozlesme testleri.

Gercek hata (12.11.2026): statik sitede /uyari POST'u 405 donuyordu; form
gonderildiginde kullaniciya hata bile gosterilmiyordu. Cozum: /api/uyari
Pages Function + D1. Bu testler sozlesmeyi (alan adlari, dogrulama kurallari)
sabitler; ag cagrisi yapmaz.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FN = ROOT / "functions" / "api" / "uyari.js"
SCHEMA = ROOT / "db" / "alerts.sql"
TEMPLATE = ROOT / "backend" / "app" / "web" / "templates" / "uyari.html"


def test_function_exists():
    assert FN.exists(), "functions/api/uyari.js yok"


def test_function_accepts_expected_fields():
    src = FN.read_text(encoding="utf-8")
    for field in ("email", "target", "target_label", "direction", "threshold_pct", "consent"):
        assert field in src, f"{field} alani islenmiyor"


def test_function_validates_email_and_consent():
    src = FN.read_text(encoding="utf-8")
    assert "EMAIL_RE" in src, "e-posta dogrulamasi yok"
    assert "consent" in src and "aydinlatma" in src.lower(), "onay kontrolu yok"


def test_function_handles_db_failure_gracefully():
    src = FN.read_text(encoding="utf-8")
    assert "env.DB" in src, "D1 binding kontrolu yok"
    assert "try" in src and "catch" in src, "hata yakalama yok"


def test_schema_matches_function_fields():
    sql = SCHEMA.read_text(encoding="utf-8")
    for col in ("email", "target", "target_label", "direction",
                "threshold_pct", "confirmed", "confirm_token", "consent_at"):
        assert col in sql, f"semada {col} kolonu yok"
    assert "UNIQUE(email, target)" in sql, "tekrar kayit engeli yok"


def test_form_posts_to_api():
    html = TEMPLATE.read_text(encoding="utf-8")
    assert 'data-api="/api/uyari"' in html, "form /api/uyari'ye baglanmamis"
    assert "alertForm" in html, "form id yok"
    assert "fetch(" in html, "JS gonderim yok"


def test_form_shows_error_to_user():
    html = TEMPLATE.read_text(encoding="utf-8")
    assert "alertLive" in html, "canli mesaj alani yok"
    assert "aria-live" in html, "erisilebilir duyuru yok"
    # sessiz yutma olmamali
    assert "Baglanti hatasi" in html, "ag hatasi kullaniciya gosterilmiyor"
