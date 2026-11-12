"""Fiyat botu: topla -> QA -> otomatik onay (esikli) -> rapor.

Gercek zamanlayici (Windows Task Scheduler) bu betigi cagirir. AI kullanmaz:
tamamen deterministik toplayici + kural tabanli QA.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from sqlalchemy import desc, select  # noqa: E402

from app.collectors import COLLECTORS  # noqa: E402
from app.collectors.gpu import GPU_COLLECTORS  # noqa: E402
from app.db import SessionLocal  # noqa: E402
from app.gpu_pipeline import ingest as gpu_ingest  # noqa: E402
from app.models import Model, PriceObservation, Provider, VerificationLog  # noqa: E402
from app.pipeline import get_or_create_provider, ingest, validate_observation  # noqa: E402

PROVIDER_META = {
    "openai": ("OpenAI", "https://openai.com", "https://openai.com/api/pricing/"),
    "anthropic": ("Anthropic", "https://www.anthropic.com", "https://www.anthropic.com/pricing"),
    "gemini": ("Google Gemini", "https://ai.google.dev", "https://ai.google.dev/gemini-api/docs/pricing"),
    "deepseek": ("DeepSeek", "https://www.deepseek.com", "https://api-docs.deepseek.com/quick_start/pricing"),
    "openrouter": ("OpenRouter", "https://openrouter.ai", "https://openrouter.ai/api/v1/models"),
}

STATE_PATH = ROOT / "data" / "bot_state.json"
LOG_PATH = ROOT / "data" / "bot_runs.jsonl"


def _load_state() -> dict:
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def _log(entry: dict) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


def collect_tokens(db, only: list[str] | None) -> dict:
    result = {"parsed": 0, "new": 0, "failed": []}
    for slug, cls in COLLECTORS.items():
        if only and slug not in only:
            continue
        collector = cls()
        name, site, pricing = PROVIDER_META[slug]
        provider = get_or_create_provider(db, slug, name, site, pricing)
        try:
            snapshot, prices = collector.collect()
        except Exception as exc:  # noqa: BLE001
            result["failed"].append(f"{slug}: {exc}")
            continue
        _run, created = ingest(
            db, provider, snapshot, prices,
            source_type=collector.source_type,
            retrieval_method=collector.retrieval_method,
            sales_channel=collector.sales_channel,
        )
        result["parsed"] += len(prices)
        result["new"] += created
    return result


def validate_pending(db) -> dict:
    passed = failed = 0
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
    return {"passed": passed, "failed": failed}


def auto_approve(db, max_change_pct: float, actor: str) -> dict:
    """Esik asilirsa ONAYLAMAZ: insan incelemesine birakir."""
    approved = held = 0
    pending = db.scalars(select(PriceObservation).where(PriceObservation.status == "pending")).all()
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
            if change > max_change_pct:
                held += 1
                continue
        obs.status = "approved"
        obs.approved_at = dt.datetime.now(dt.timezone.utc)
        obs.approved_by = actor
        db.add(obs)
        approved += 1
    db.commit()
    return {"approved": approved, "held_for_review": held}


def collect_gpu(db, only: list[str] | None) -> dict:
    result = {"quotes": 0, "new": 0, "failed": []}
    for cls in GPU_COLLECTORS:
        collector = cls()
        if only and collector.slug not in only:
            continue
        try:
            snapshot = collector.collect()
        except Exception as exc:  # noqa: BLE001
            result["failed"].append(f"{collector.slug}: {exc}")
            continue
        if not snapshot.quotes:
            continue
        created, _skipped = gpu_ingest(db, snapshot)
        result["quotes"] += len(snapshot.quotes)
        result["new"] += created
    return result


def main() -> int:
    ap = argparse.ArgumentParser(description="TokenMaliyet fiyat botu")
    ap.add_argument("--skip-gpu", action="store_true")
    ap.add_argument("--skip-tokens", action="store_true")
    ap.add_argument("--only", default="", help="virgulle ayrilmis saglayici listesi")
    ap.add_argument("--max-change-pct", type=float, default=float(os.getenv("BOT_MAX_CHANGE_PCT", "30")))
    ap.add_argument("--no-approve", action="store_true", help="sadece topla, onaylama")
    args = ap.parse_args()

    started = dt.datetime.now(dt.timezone.utc)
    only = [s.strip() for s in args.only.split(",") if s.strip()] or None

    with SessionLocal() as db:
        summary: dict = {"started_at": started.isoformat(), "only": only}
        if not args.skip_tokens:
            summary["tokens"] = collect_tokens(db, only)
            summary["qa"] = validate_pending(db)
            if not args.no_approve:
                summary["approval"] = auto_approve(db, args.max_change_pct, actor="bot")
        if not args.skip_gpu:
            summary["gpu"] = collect_gpu(db, only)

        summary["finished_at"] = dt.datetime.now(dt.timezone.utc).isoformat()

    state = _load_state()
    state["last_run"] = summary["finished_at"]
    state["last_summary"] = summary
    state["runs"] = state.get("runs", 0) + 1
    _save_state(state)
    _log(summary)

    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())