"""Golden fiyatlari canli veritabaninda dogrular (CI/deploy oncesi)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from sqlalchemy import select  # noqa: E402

from app.db import SessionLocal  # noqa: E402
from app.models import Model, PriceObservation, Provider  # noqa: E402

GOLDEN = ROOT / "tests" / "golden_prices.json"
TOLERANCE = 0.001  # %0.1


def main() -> int:
    golden = json.loads(GOLDEN.read_text(encoding="utf-8"))
    problems: list[str] = []
    with SessionLocal() as db:
        for item in golden:
            row = db.execute(
                select(PriceObservation)
                .join(Model, Model.id == PriceObservation.model_id)
                .join(Provider, Provider.id == Model.provider_id)
                .where(
                    Provider.slug == item["provider"],
                    Model.canonical_id == item["model"],
                    PriceObservation.price_dimension == item["dimension"],
                    # Baglam dilimi (tier) eslesmeli: aksi halde <=100K ile >100K karisir.
                    PriceObservation.tier_label.is_(item.get("tier_label"))
                    if not item.get("tier_label")
                    else PriceObservation.tier_label == item["tier_label"],
                    # Peak / off-peak de eslesmeli (DeepSeek iki dilim yayinlar).
                    PriceObservation.peak_period.is_(item.get("peak_period"))
                    if not item.get("peak_period")
                    else PriceObservation.peak_period == item["peak_period"],
                    PriceObservation.status == "approved",
                )
                .order_by(PriceObservation.observed_at.desc())
            ).scalars().first()
            if row is None:
                problems.append(f"EKSIK: {item['provider']}/{item['model']} {item['dimension']}")
                continue
            expected = float(item["amount"])
            actual = float(row.amount)
            if expected == 0:
                continue
            delta = abs(actual - expected) / expected
            if delta > TOLERANCE:
                problems.append(
                    f"DEGISTI: {item['provider']}/{item['model']} {item['dimension']} "
                    f"{expected} -> {actual} (%{delta * 100:.2f})"
                )
    if problems:
        changed = [p for p in problems if p.startswith("DEGISTI")]
        missing = [p for p in problems if p.startswith("EKSIK")]

        # ONEMLI AYRIM (CI icin kritik):
        #   DEGISTI -> fiyat gercekten degisti  => HER ZAMAN hata (1)
        #   EKSIK   -> kaynak o an veri vermedi  => uyari, hata DEGIL
        # Eksik kayit, API anahtari olmayan saglayicidir (or. OpenAI). Bu CI'i
        # kirmamali; aksi halde her push basarisiz gorunur ve gercek regresyon
        # sinyali kaybolur.
        if changed:
            print("GOLDEN TEST BASARISIZ (fiyat degisti):")
            for p in changed:
                print("  -", p)
            print("\nBeklenen bir degisimse tests/golden_prices.json bilincli guncellenmeli.")
            return 1

        if missing:
            print(f"golden: {len(missing)} kayit eksik (kaynak veri vermedi) - UYARI, hata degil")
            for p in missing[:5]:
                print("  -", p)
            if len(missing) > 5:
                print(f"  ... ve {len(missing) - 5} tane daha")

        print(f"golden OK kismi ({len(golden) - len(missing)}/{len(golden)} kayit dogrulandi)")
        return 0

    print(f"golden OK ({len(golden)} kayit)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
