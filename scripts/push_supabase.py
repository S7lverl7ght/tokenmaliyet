"""Bugunku fiyatlari Supabase'e yazar (kalici gecmis).

GitHub Actions akisi:
  1) topla (yerel Postgres, uçucu)
  2) push_supabase.py -> kalici gecmise ekle
  3) alert_changes_supabase.py -> degisimleri oku
  4) /api/bildir -> e-posta
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from sqlalchemy import select  # noqa: E402

from app.db import SessionLocal  # noqa: E402
from app.models import ExchangeRate, Model, PriceObservation, Provider  # noqa: E402


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
    dsn = dsn_from_env()
    if not dsn:
        print("Supabase yapilandirilmamis, atlandi")
        return 0
    try:
        import psycopg
    except ImportError:
        print("psycopg yok")
        return 1

    with SessionLocal() as db:
        provs = db.scalars(select(Provider)).all()
        models = db.scalars(select(Model)).all()
        obs = db.scalars(
            select(PriceObservation).where(PriceObservation.status == "approved")
        ).all()
        fx = db.scalars(select(ExchangeRate)).all()

    prov_by_id = {p.id: p for p in provs}
    model_by_id = {m.id: m for m in models}

    with psycopg.connect(dsn, connect_timeout=30) as conn:
        with conn.cursor() as cur:
            # saglayicilar (upsert)
            cur.executemany(
                """insert into providers (slug, name, website, pricing_url)
                   values (%s,%s,%s,%s)
                   on conflict (slug) do update set name = excluded.name""",
                [(p.slug, p.name, p.website, p.pricing_url) for p in provs],
            )
            cur.execute("select slug, id from providers")
            pmap = dict(cur.fetchall())

            cur.executemany(
                """insert into models (provider_id, canonical_id, display_name)
                   values (%s,%s,%s)
                   on conflict (provider_id, canonical_id)
                   do update set display_name = excluded.display_name""",
                [
                    (pmap[prov_by_id[m.provider_id].slug], m.canonical_id, m.display_name)
                    for m in models
                    if m.provider_id in prov_by_id
                ],
            )
            cur.execute("select canonical_id, id from models")
            mmap: dict[str, int] = {}
            for cid, mid in cur.fetchall():
                mmap.setdefault(cid, mid)

            rows = []
            for o in obs:
                m = model_by_id.get(o.model_id)
                if not m or m.canonical_id not in mmap:
                    continue
                rows.append(
                    (mmap[m.canonical_id], o.price_dimension, o.amount, o.currency,
                     o.billing_unit, o.tier_label, o.peak_period, o.observed_at, "approved")
                )
            if rows:
                cur.executemany(
                    """insert into price_observations
                       (model_id, price_dimension, amount, currency, billing_unit,
                        tier_label, peak_period, observed_at, status)
                       values (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                       on conflict do nothing""",
                    rows,
                )
            if fx:
                cur.executemany(
                    """insert into exchange_rates
                       (base_currency, quote_currency, rate, source_url, effective_at)
                       values (%s,%s,%s,%s,%s)
                       on conflict do nothing""",
                    [(r.base_currency, r.quote_currency, r.rate, r.source_url, r.effective_at)
                     for r in fx],
                )
        conn.commit()
        with conn.cursor() as cur:
            cur.execute("select count(*) from price_observations")
            print(f"Supabase fiyat satiri: {cur.fetchone()[0]} (+{len(rows)} eklendi)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
