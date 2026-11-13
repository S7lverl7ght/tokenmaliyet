"""Supabase kalici gecmis entegrasyonu testleri (rapor 5. tur Hata 5).

Kok neden: GitHub Actions Postgres'i her calismada sifirlaniyordu; dunku fiyat
olmadigi icin alert_changes.py hicbir degisim yakalayamiyor, e-posta gitmiyordu.
Cozum: kalici Supabase + v_price_changes gorunumu.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(p):
    return p.read_text(encoding="utf-8")


def test_schema_has_price_history():
    s = read(ROOT / "db" / "supabase_schema.sql")
    assert "price_observations" in s
    assert "v_price_changes" in s
    # ayni model+kalem icin tek onayli fiyat
    assert "uq_price_approved" in s


def test_view_pairs_distinct_observations():
    """Gorunum eski ve yeni AYRI gozlemleri eslestirmeli; aksi halde pct=0 cikar."""
    s = read(ROOT / "db" / "supabase_schema.sql")
    view = s[s.index("create or replace view v_price_changes"):]
    assert "o.observed_at < n.observed_at" in view, "ayni gozlem eslesmemeli"
    assert "distinct on" in view.lower()


def test_push_script_uses_env_credentials():
    s = read(ROOT / "scripts" / "push_supabase.py")
    assert "SUPABASE_DB_URL" in s
    assert "SUPABASE_DB_PASSWORD" in s
    assert "SUPABASE_PROJECT_REF" in s
    # sifre kodda olmamali
    assert "0x4AAAA" not in s


def test_alert_script_reads_supabase():
    s = read(ROOT / "scripts" / "alert_changes_supabase.py")
    assert "v_price_changes" in s
    assert "SUPABASE_DB_URL" in s


def test_ci_wires_supabase():
    s = read(ROOT / ".github" / "workflows" / "refresh.yml")
    assert "push_supabase.py" in s
    assert "alert_changes_supabase.py" in s
    assert "SUPABASE_DB_PASSWORD" in s
    # eski uçucu script kalmamali
    assert "python scripts/alert_changes.py" not in s
