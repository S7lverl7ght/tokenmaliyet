"""GPU kiralama fiyatlarini toplar (5 kaynak). Sahte fiyat uretmez."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.collectors.gpu import GPU_COLLECTORS  # noqa: E402
from app.db import SessionLocal  # noqa: E402
from app.gpu_pipeline import ingest  # noqa: E402


def main(argv: list[str]) -> int:
    wanted = {a.lower() for a in argv}
    total_new = total_skip = 0
    with SessionLocal() as db:
        for cls in GPU_COLLECTORS:
            collector = cls()
            if wanted and collector.slug not in wanted:
                continue
            try:
                snapshot = collector.collect()
            except Exception as exc:  # noqa: BLE001
                print(f"[fail] {collector.slug}: {exc}")
                continue
            if not snapshot.quotes:
                print(f"[warn] {collector.slug}: fiyat satiri ayiklanamadi (sayfa yapisi degismis olabilir)")
                continue
            created, skipped = ingest(db, snapshot)
            total_new += created
            total_skip += skipped
            print(f"[ok] {collector.slug}: quotes={len(snapshot.quotes)} new={created} skipped={skipped}")
    print(f"TOTAL new={total_new} skipped={total_skip}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
