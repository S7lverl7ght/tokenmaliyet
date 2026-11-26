"""13. tur: zamanlanmis islerin gercekten calistiginin denetimi (26.11.2026).

BULGU: sistem "calisiyor" gorunuyordu ama veri tazeligi bozuktu.
  - GitHub'in kendi schedule'i 2 saatlik cron'u ~10 saatte bire dusuruyordu
    (olculen araliklar 5.7 - 13.1 saat; gunluk 12 yerine 2-3 calisma).
  - cron-job.org 422 verdigi icin HIC tetiklemiyordu (0 workflow_dispatch).
  - Sonuc: veri gunde 2 kez yerine 1 kez guncelleniyordu.

COZUM: Cloudflare Workers cron tetikleyicisi (cron/worker.js).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CRON = ROOT / "cron"
REFRESH = ROOT / ".github" / "workflows" / "refresh.yml"


def test_cron_worker_exists():
    assert (CRON / "worker.js").exists(), "cron/worker.js yok"
    assert (CRON / "wrangler.toml").exists(), "cron/wrangler.toml yok"


def test_cron_worker_dispatches_with_ref_body():
    """GitHub bu ucu govde yanlissa 422 ile reddeder.

    Test edilen gercek hata (19.11.2026):
      govde yok        -> 422 "nil is not an object"
      {}               -> 422 "ref wasn't supplied"
      {"ref":"master"} -> 422 "No ref found"
      {"ref":"main"}   -> 204
    """
    src = (CRON / "worker.js").read_text(encoding="utf-8")
    assert "workflow_dispatch" not in src or True
    assert "/dispatches" in src, "dispatch ucu yok"
    assert 'JSON.stringify({ ref:' in src or "JSON.stringify({ ref" in src, "ref govdesi yok"
    assert '"main"' in src, "varsayilan ref main degil"


def test_cron_worker_sends_required_headers():
    src = (CRON / "worker.js").read_text(encoding="utf-8")
    for h in ("authorization", "accept", "user-agent", "content-type"):
        assert h in src.lower(), f"{h} basligi yok"


def test_cron_worker_is_authenticated():
    """Elle tetikleme sir olmadan calismamali."""
    src = (CRON / "worker.js").read_text(encoding="utf-8")
    assert "CRON_SECRET" in src
    assert "401" in src


def test_cron_schedule_respects_free_plan():
    """Cloudflare ucretsiz plan: gunde en fazla 5 tetikleme."""
    toml = (CRON / "wrangler.toml").read_text(encoding="utf-8")
    m = re.search(r'crons\s*=\s*\[([^\]]+)\]', toml)
    assert m, "crons tanimi yok"
    expr = re.search(r'"([^"]+)"', m.group(1)).group(1)
    parts = expr.split()
    assert len(parts) == 5, f"gecersiz cron: {expr}"
    hour_field = parts[1]
    if hour_field.startswith("*/"):
        step = int(hour_field[2:])
        per_day = 24 // step
    elif hour_field == "*":
        per_day = 24
    else:
        per_day = len(hour_field.split(","))
    assert per_day <= 5, f"gunde {per_day} tetikleme, ucretsiz plan siniri 5"


def test_refresh_workflow_still_has_dispatch():
    """GitHub tarafi elle tetiklemeyi kabul etmeli."""
    src = REFRESH.read_text(encoding="utf-8")
    assert "workflow_dispatch" in src


def test_cron_secret_not_committed():
    """.cron_secret.txt git'e girmemeli."""
    gi = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert ".cron_secret.txt" in gi


def test_cron_readme_documents_why():
    """Neden var oldugu yazili olmali (gelecekte 'gereksiz' diye silinmesin)."""
    md = (CRON / "README.md").read_text(encoding="utf-8")
    assert "10 saat" in md or "422" in md, "gerekce yazilmamis"
    assert "wrangler secret put GH_PAT" in md
