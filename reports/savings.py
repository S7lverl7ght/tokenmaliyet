"""Kazanc urunu #2: model degistirme tasarruf hesaplayici (CLI).

Ornek:
  python reports/savings.py --from gemini-3.1-pro-preview --to deepseek-v4-pro \
      --input-tokens 80000000 --output-tokens 20000000
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from sqlalchemy import desc, select  # noqa: E402

from app.db import SessionLocal  # noqa: E402
from app.models import DataSource, ExchangeRate, Model, PriceObservation, Provider  # noqa: E402


def load(db) -> dict[str, dict]:
    rows = db.execute(
        select(PriceObservation, Model, Provider, DataSource)
        .join(Model, Model.id == PriceObservation.model_id)
        .join(Provider, Provider.id == Model.provider_id)
        .join(DataSource, DataSource.id == PriceObservation.source_id)
        .where(PriceObservation.status == "approved")
        .order_by(desc(PriceObservation.observed_at))
    ).all()
    out: dict[str, dict] = {}
    for obs, model, provider, source in rows:
        if obs.normalized_usd_per_1m is None or obs.price_dimension not in ("input", "output"):
            continue
        entry = out.setdefault(model.canonical_id, {
            "provider": provider.slug, "channel": source.sales_channel, "dims": {},
            "source": source.source_url,
        })
        entry["dims"].setdefault(obs.price_dimension, float(obs.normalized_usd_per_1m))
    return out


def cost(entry: dict, in_tok: int, out_tok: int) -> float:
    return (entry["dims"].get("input", 0) * in_tok + entry["dims"].get("output", 0) * out_tok) / 1_000_000


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="src", required=False)
    ap.add_argument("--to", dest="dst", required=False)
    ap.add_argument("--input-tokens", type=int, required=True)
    ap.add_argument("--output-tokens", type=int, required=True)
    ap.add_argument("--top", type=int, default=10)
    args = ap.parse_args()

    with SessionLocal() as db:
        fx = db.scalars(select(ExchangeRate).where(ExchangeRate.quote_currency == "TRY")
                        .order_by(desc(ExchangeRate.effective_at))).first()
        rate = float(fx.rate) if fx else 0.0
        prices = load(db)
        usable = {k: v for k, v in prices.items() if "input" in v["dims"] and "output" in v["dims"]}
        ranked = sorted(usable.items(), key=lambda kv: cost(kv[1], args.input_tokens, args.output_tokens))

        if args.src and args.dst:
            if args.src not in usable or args.dst not in usable:
                print(f"model bulunamadi. Ornekler: {', '.join(list(usable)[:5])}")
                return 1
            a = cost(usable[args.src], args.input_tokens, args.output_tokens)
            b = cost(usable[args.dst], args.input_tokens, args.output_tokens)
            print(json.dumps({
                "from": {"model": args.src, "usd": round(a, 2), "try": round(a * rate, 0)},
                "to": {"model": args.dst, "usd": round(b, 2), "try": round(b * rate, 0)},
                "monthly_saving_try": round((a - b) * rate, 0),
                "yearly_saving_try": round((a - b) * rate * 12, 0),
                "saving_pct": round((1 - b / a) * 100, 1) if a else None,
                "fx": rate,
            }, ensure_ascii=False, indent=2))
            return 0

        print(f"{'model':<40}{'saglayici':<11}{'USD/ay':>10}{'TRY/ay':>12}")
        for name, entry in ranked[: args.top]:
            usd = cost(entry, args.input_tokens, args.output_tokens)
            print(f"{name[:39]:<40}{entry['provider']:<11}{usd:>10,.0f}{usd * rate:>12,.0f}")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
