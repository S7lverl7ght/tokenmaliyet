"""Supabase'den fiyat degisimlerini okur, /api/bildir formatina cevirir.

Neden: GitHub Actions'taki Postgres her calismada sifirlaniyordu; bu yuzden
dunku fiyat olmadigi icin hicbir degisim yakalanamiyordu (rapor 5. tur Hata 5).
Artik gecmis Supabase'de kalici; bu betik oradan okur.

Kullanim:
    python scripts/alert_changes_supabase.py --out data/alert_changes.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def dsn_from_env() -> str:
    url = os.getenv("SUPABASE_DB_URL", "").strip()
    if url:
        return url
    pw = os.getenv("SUPABASE_DB_PASSWORD", "").strip()
    ref = os.getenv("SUPABASE_PROJECT_REF", "").strip()
    if not pw or not ref:
        return ""
    return (
        f"postgresql://postgres.{ref}:{pw}"
        f"@aws-1-ap-southeast-1.pooler.supabase.com:5432/postgres?sslmode=require"
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "data" / "alert_changes.json"))
    ap.add_argument("--min-pct", type=float, default=1.0)
    args = ap.parse_args()

    dsn = dsn_from_env()
    if not dsn:
        print("SUPABASE_DB_URL veya SUPABASE_DB_PASSWORD + PROJECT_REF gerekli")
        Path(args.out).write_text('{"changes": []}', encoding="utf-8")
        return 0

    try:
        import psycopg
    except ImportError:
        print("psycopg kurulu degil")
        return 1

    changes: list[dict] = []
    try:
        with psycopg.connect(dsn, connect_timeout=25) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    select provider_slug, canonical_id, display_name,
                           price_dimension, old_amount, new_amount, pct_change
                    from v_price_changes
                    where pct_change is not null
                      and abs(pct_change) >= %s
                    order by abs(pct_change) desc
                    limit 200
                    """,
                    (args.min_pct,),
                )
                for prov, cid, name, dim, old, new, pct in cur.fetchall():
                    changes.append({
                        "target": f"{prov}|{cid}|",
                        "target_label": f"{prov} · {name} ({dim})",
                        "old_price": float(old),
                        "new_price": float(new),
                    })
    except Exception as exc:
        print("Supabase okunamadi:", str(exc)[:120])
        Path(args.out).write_text('{"changes": []}', encoding="utf-8")
        return 0

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"changes": changes}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(changes)} degisim -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
