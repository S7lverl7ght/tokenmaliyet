"""Fiyat degisimlerini tespit edip /api/bildir'e gonderilecek JSON'u uretir.

Kullanim:
    python scripts/alert_changes.py --out data/alert_changes.json

Mantik: son 24 saatte degisen (model, kalem) fiyatlarini bulur; esik ustundekileri
bildirime uygun formata cevirir. Gercek gonderim /api/bildir tarafinda yapilir.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from sqlalchemy import select  # noqa: E402

from app.db import SessionLocal  # noqa: E402
from app.models import Model, PriceObservation, Provider  # noqa: E402

# Bildirim yalnizca bu kalemler icin anlamli (token fiyatlari).
NOTIFY_DIMENSIONS = {"input", "output"}
PER_MILLION = {"USD/1M_tokens": 1.0, "USD/1K_tokens": 1000.0, "USD/token": 1_000_000.0}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "data" / "alert_changes.json"))
    ap.add_argument("--hours", type=int, default=36)
    ap.add_argument("--min-pct", type=float, default=1.0)
    args = ap.parse_args()

    since = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=args.hours)
    changes: list[dict] = []

    with SessionLocal() as db:
        rows = db.execute(
            select(PriceObservation, Model, Provider)
            .join(Model, Model.id == PriceObservation.model_id)
            .join(Provider, Provider.id == Model.provider_id)
            .where(PriceObservation.status == "approved")
            .where(PriceObservation.price_dimension.in_(NOTIFY_DIMENSIONS))
            .order_by(PriceObservation.observed_at.desc())
        ).all()

        # (model_id, dimension, peak) -> en yeni iki gozlem
        hist: dict[tuple, list] = {}
        for obs, model, prov in rows:
            key = (model.id, obs.price_dimension, obs.peak_period)
            hist.setdefault(key, []).append((obs, model, prov))

        for key, items in hist.items():
            if len(items) < 2:
                continue
            newest, model, prov = items[0]
            if newest.observed_at < since:
                continue
            oldest = items[-1][0]
            factor = PER_MILLION.get(newest.billing_unit, 1.0)
            new_v = float(newest.amount) * factor
            old_v = float(oldest.amount) * factor
            if old_v <= 0:
                continue
            pct = (new_v - old_v) / old_v * 100
            if abs(pct) < args.min_pct:
                continue
            from app.web.queries import split_variant

            base, _ = split_variant(model.canonical_id)
            changes.append({
                "target": f"{prov.slug}|{base}|",
                "target_label": f"{prov.name} · {model.display_name} ({newest.price_dimension})",
                "old_price": round(old_v, 6),
                "new_price": round(new_v, 6),
            })

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"changes": changes}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(changes)} degisim -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
