"""Run deterministic QA checks on pending observations (no auto publish)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from sqlalchemy import select  # noqa: E402

from app.db import SessionLocal  # noqa: E402
from app.models import PriceObservation, VerificationLog  # noqa: E402
from app.pipeline import validate_observation  # noqa: E402


def main() -> int:
    passed = failed = 0
    with SessionLocal() as db:
        pending = db.scalars(select(PriceObservation).where(PriceObservation.status == "pending")).all()
        for obs in pending:
            has_logs = db.scalar(select(VerificationLog.id).where(VerificationLog.observation_id == obs.id))
            if has_logs:
                continue
            if validate_observation(db, obs):
                passed += 1
            else:
                failed += 1
        db.commit()
    print(f"QA: passed={passed} failed={failed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
