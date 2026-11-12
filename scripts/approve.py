"""Human approval gate. Nothing is published without this step.

Usage:
  python scripts/approve.py --list
  python scripts/approve.py --auto --actor omer --max-change-pct 25
  python scripts/approve.py --ids 12,13 --actor omer
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from sqlalchemy import desc, select  # noqa: E402

from app.db import SessionLocal  # noqa: E402
from app.models import Model, PriceObservation, Provider, VerificationLog  # noqa: E402
from app.pipeline import approve  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--ids")
    ap.add_argument("--auto", action="store_true")
    ap.add_argument("--actor", default="operator")
    ap.add_argument("--max-change-pct", type=float, default=30.0)
    args = ap.parse_args()

    with SessionLocal() as db:
        pending = db.scalars(select(PriceObservation).where(PriceObservation.status == "pending")).all()
        if args.list or not (args.ids or args.auto):
            for obs in pending:
                model = db.get(Model, obs.model_id)
                provider = db.get(Provider, model.provider_id) if model else None
                print(f"{obs.id:>5} | {provider.slug if provider else '?':<10} | {model.canonical_id if model else '?':<28}"
                      f" | {obs.price_dimension:<12} | {obs.amount} {obs.currency}/{obs.billing_unit}"
                      f" | {obs.peak_period or '-'}")
            print(f"pending: {len(pending)}")
            return 0

        targets = []
        if args.ids:
            ids = [int(x) for x in args.ids.split(",") if x.strip()]
            targets = [o for o in pending if o.id in ids]
        elif args.auto:
            for obs in pending:
                fails = db.scalars(
                    select(VerificationLog).where(
                        VerificationLog.observation_id == obs.id, VerificationLog.result == "fail"
                    )
                ).all()
                if fails:
                    continue
                prev = db.scalars(
                    select(PriceObservation)
                    .where(
                        PriceObservation.model_id == obs.model_id,
                        PriceObservation.price_dimension == obs.price_dimension,
                        PriceObservation.status == "approved",
                        PriceObservation.id != obs.id,
                    )
                    .order_by(desc(PriceObservation.observed_at))
                ).first()
                if prev is not None and float(prev.amount) > 0:
                    change = abs(float(obs.amount) - float(prev.amount)) / float(prev.amount) * 100
                    if change > args.max_change_pct:
                        print(f"[hold] {obs.id}: price change {change:.1f}% exceeds {args.max_change_pct}% - manual review")
                        continue
                targets.append(obs)

        ok = 0
        for obs in targets:
            if approve(db, obs, args.actor):
                ok += 1
        db.commit()
        print(f"approved: {ok}/{len(targets)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())