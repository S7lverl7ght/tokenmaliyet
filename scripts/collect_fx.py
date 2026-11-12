"""Store dated USD/TRY exchange rate (source + timestamp preserved)."""
from __future__ import annotations

import datetime as dt
import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.collectors.base import fetch_json  # noqa: E402
from app.config import settings  # noqa: E402
from app.db import SessionLocal  # noqa: E402
from app.models import ExchangeRate  # noqa: E402


def main() -> int:
    data, _raw, _url = fetch_json(settings.fx_endpoint)
    rate = Decimal(str(data["rates"]["TRY"]))
    effective = dt.datetime.fromisoformat(data["date"] + "T00:00:00+00:00")
    with SessionLocal() as db:
        exists = db.query(ExchangeRate).filter_by(effective_at=effective, quote_currency="TRY").first()
        if exists is None:
            db.add(ExchangeRate(base_currency="USD", quote_currency="TRY", rate=rate,
                                effective_at=effective, source_url=settings.fx_endpoint))
            db.commit()
    print(f"USD/TRY {rate} @ {data['date']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
