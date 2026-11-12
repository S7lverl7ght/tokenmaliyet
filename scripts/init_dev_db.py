"""Dev-only schema bootstrap (create_all). Production uses Alembic."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.db import Base, engine  # noqa: E402
from app import models  # noqa: F401,E402


def main() -> None:
    Base.metadata.create_all(engine)
    names = ", ".join(sorted(Base.metadata.tables))
    print(f"created tables: {names}")


if __name__ == "__main__":
    main()
