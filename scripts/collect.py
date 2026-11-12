"""Collect raw snapshots + pending observations from every provider adapter."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.collectors import COLLECTORS  # noqa: E402
from app.db import SessionLocal  # noqa: E402
from app.pipeline import get_or_create_provider, ingest  # noqa: E402

PROVIDER_META = {
    "openai": ("OpenAI", "https://openai.com", "https://openai.com/api/pricing/"),
    "anthropic": ("Anthropic", "https://www.anthropic.com", "https://www.anthropic.com/pricing"),
    "gemini": ("Google Gemini", "https://ai.google.dev", "https://ai.google.dev/gemini-api/docs/pricing"),
    "deepseek": ("DeepSeek", "https://www.deepseek.com", "https://api-docs.deepseek.com/quick_start/pricing"),
    "openrouter": ("OpenRouter", "https://openrouter.ai", "https://openrouter.ai/api/v1/models"),
}


def main(argv: list[str]) -> int:
    targets = argv or list(COLLECTORS)
    total = 0
    with SessionLocal() as db:
        for slug in targets:
            cls = COLLECTORS.get(slug)
            if cls is None:
                print(f"[skip] unknown provider {slug}")
                continue
            collector = cls()
            name, site, pricing = PROVIDER_META[slug]
            provider = get_or_create_provider(db, slug, name, site, pricing)
            try:
                snapshot, prices = collector.collect()
            except Exception as exc:  # noqa: BLE001
                print(f"[fail] {slug}: {exc}")
                continue
            run, created = ingest(
                db, provider, snapshot, prices,
                source_type=collector.source_type,
                retrieval_method=collector.retrieval_method,
                sales_channel=collector.sales_channel,
            )
            total += created
            print(f"[ok] {slug}: parsed={len(prices)} new_pending={created} run={run.id} raw={snapshot.snapshot_path}")
    print(f"TOTAL new pending observations: {total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
