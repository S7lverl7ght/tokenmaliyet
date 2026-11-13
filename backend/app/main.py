from __future__ import annotations

import datetime as dt
from decimal import Decimal

from pathlib import Path

import os

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from . import __version__
from .db import get_session, ping
from .models import DataSource, ExchangeRate, Model, PriceObservation, Provider
from .web.admin import router as admin_router
from .web.routes import router as web_router

app = FastAPI(
    title="AI Maliyet Merkezi",
    version=__version__,
    description="Kaynakli, dogrulanmis ve tarihcesi korunmus AI API fiyat motoru (V0.1)",
)

# --- üretim ara yazılımı -------------------------------------------------
app.add_middleware(GZipMiddleware, minimum_size=800)

IS_PROD = os.getenv("APP_ENV", "dev") == "production"


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    response.headers.setdefault(
        "Content-Security-Policy",
        "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; "
        "script-src 'self' 'unsafe-inline' https://static.cloudflareinsights.com https://challenges.cloudflare.com; connect-src 'self' https://cloudflareinsights.com https://challenges.cloudflare.com; frame-ancestors 'self'; base-uri 'self'",
    )
    if IS_PROD:
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    # Statik varlıklar sürümlü; uzun önbellek güvenli.
    if request.url.path.startswith("/static/"):
        response.headers.setdefault("Cache-Control", "public, max-age=31536000, immutable")
    elif request.url.path.startswith("/api/"):
        response.headers.setdefault("Cache-Control", "public, max-age=60")
    return response


app.mount("/static", StaticFiles(directory=str(Path(__file__).parent / "web" / "static")), name="static")

APPROVED = "approved"


@app.get("/api", include_in_schema=False)
def api_identity() -> dict:
    return {"service": "ai-maliyet-merkezi", "version": __version__, "status": "ok",
            "policy": "Yalnizca QA onayli fiyatlar sunulur.",
            "ui": f"{app.state.site_url if hasattr(app.state, 'site_url') else ''}/fiyatlar"}


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "ts": dt.datetime.now(dt.timezone.utc).isoformat()}


@app.get("/health/db")
def health_db(session: Session = Depends(get_session)) -> dict:
    try:
        ping()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail=f"db unavailable: {exc}") from exc
    return {"status": "ok", "database": "connected"}


@app.get("/health/full")
def health_full(session: Session = Depends(get_session)) -> dict:
    """Dağıtım/izleme için: DB, veri tazeliği ve onaylı kayıt sayısı."""
    out: dict = {"status": "ok", "version": __version__}
    try:
        ping()
        out["database"] = "connected"
    except Exception as exc:  # noqa: BLE001
        return JSONResponse(status_code=503, content={"status": "degraded", "database": str(exc)[:200]})

    latest = session.scalar(select(func.max(PriceObservation.observed_at)))
    approved = session.scalar(
        select(func.count(PriceObservation.id)).where(PriceObservation.status == "approved")
    )
    age_hours = None
    if latest is not None:
        age_hours = round((dt.datetime.now(dt.timezone.utc) - latest).total_seconds() / 3600, 1)
    out.update({
        "approved_observations": int(approved or 0),
        "last_observation": latest.isoformat() if latest else None,
        "data_age_hours": age_hours,
        "stale": bool(age_hours is not None and age_hours > 48),
    })
    if out["stale"]:
        out["status"] = "degraded"
    return out


@app.get("/api/v1/providers")
def list_providers(session: Session = Depends(get_session)) -> list[dict]:
    rows = session.scalars(select(Provider).where(Provider.is_active.is_(True)).order_by(Provider.name)).all()
    return [
        {"id": p.id, "slug": p.slug, "name": p.name, "website": p.website, "pricing_url": p.pricing_url}
        for p in rows
    ]


@app.get("/api/v1/models")
def list_models(provider_id: int | None = None, session: Session = Depends(get_session)) -> list[dict]:
    stmt = select(Model).where(Model.is_active.is_(True))
    if provider_id:
        stmt = stmt.where(Model.provider_id == provider_id)
    rows = session.scalars(stmt.order_by(Model.provider_id, Model.canonical_id)).all()
    return [
        {"id": m.id, "provider_id": m.provider_id, "canonical_id": m.canonical_id,
         "display_name": m.display_name, "modalities": m.modalities}
        for m in rows
    ]


def _price_rows(session: Session, model_id: int | None, provider_id: int | None) -> list[tuple]:
    stmt = (
        select(PriceObservation, Model, Provider, DataSource)
        .join(Model, Model.id == PriceObservation.model_id)
        .join(Provider, Provider.id == Model.provider_id)
        .join(DataSource, DataSource.id == PriceObservation.source_id)
        .where(PriceObservation.status == APPROVED)
    )
    if model_id:
        stmt = stmt.where(PriceObservation.model_id == model_id)
    if provider_id:
        stmt = stmt.where(Model.provider_id == provider_id)
    return session.execute(stmt.order_by(desc(PriceObservation.observed_at))).all()


@app.get("/api/v1/prices")
def list_prices(
    model_id: int | None = Query(default=None),
    provider_id: int | None = Query(default=None),
    session: Session = Depends(get_session),
) -> list[dict]:
    """Yalnizca onaylanmis (approved) fiyatlar. Her model + boyut icin en guncel kayit doner."""
    latest: dict[tuple, dict] = {}
    for obs, model, provider, source in _price_rows(session, model_id, provider_id):
        key = (model.canonical_id, obs.price_dimension, obs.peak_period)
        if key in latest:
            continue
        latest[key] = {
            "observation_id": obs.id,
            "provider": provider.slug,
            "model_id": model.canonical_id,
            "display_name": model.display_name,
            "price_dimension": obs.price_dimension,
            "amount": float(obs.amount),
            "currency": obs.currency,
            "billing_unit": obs.billing_unit,
            "usd_per_1m_tokens": float(obs.normalized_usd_per_1m) if obs.normalized_usd_per_1m else None,
            "peak_period": obs.peak_period,
            "tier_label": obs.tier_label,
            "observed_at": obs.observed_at.isoformat(),
            "effective_from": obs.effective_from.isoformat() if obs.effective_from else None,
            "source_url": source.source_url,
            "sales_channel": source.sales_channel,
        }
    return list(latest.values())


@app.get("/api/v1/prices/history/{model_id}")
def price_history(model_id: int, session: Session = Depends(get_session)) -> list[dict]:
    rows = _price_rows(session, model_id, None)
    return [
        {
            "observed_at": obs.observed_at.isoformat(),
            "price_dimension": obs.price_dimension,
            "amount": float(obs.amount),
            "currency": obs.currency,
            "billing_unit": obs.billing_unit,
            "peak_period": obs.peak_period,
        }
        for obs, _m, _p, _s in rows
    ]


@app.get("/api/v1/fx")
def fx_rate(quote: str = "TRY", session: Session = Depends(get_session)) -> dict:
    row = session.scalars(
        select(ExchangeRate).where(ExchangeRate.quote_currency == quote).order_by(desc(ExchangeRate.effective_at))
    ).first()
    if row is None:
        raise HTTPException(status_code=404, detail="no rate")
    return {"base": row.base_currency, "quote": row.quote_currency, "rate": float(row.rate),
            "effective_at": row.effective_at.isoformat(), "source_url": row.source_url}


@app.get("/api/v1/estimate")
def estimate(
    model_id: int,
    input_tokens: int = 1000,
    output_tokens: int = 500,
    quote: str | None = None,
    session: Session = Depends(get_session),
) -> dict:
    """Tek cagri/yuk maliyet tahmini: onayli fiyatlar + tarihli kur ile TRY karsiligi."""
    rows = [r for r in _price_rows(session, model_id, None)]
    if not rows:
        raise HTTPException(status_code=404, detail="no approved price for model")
    per_dim: dict[str, Decimal] = {}
    for obs, _m, _p, _s in rows:
        if obs.normalized_usd_per_1m is not None and obs.price_dimension not in per_dim:
            per_dim[obs.price_dimension] = obs.normalized_usd_per_1m
    inp = per_dim.get("input")
    out = per_dim.get("output")
    if inp is None or out is None:
        raise HTTPException(status_code=409, detail="input/output price missing")
    usd = (inp * input_tokens + out * output_tokens) / Decimal(1_000_000)
    result = {"model_id": model_id, "usd": float(round(usd, 6))}
    if quote:
        rate = session.scalars(
            select(ExchangeRate).where(ExchangeRate.quote_currency == quote).order_by(desc(ExchangeRate.effective_at))
        ).first()
        if rate:
            result["converted"] = {quote: float(round(usd * rate.rate, 4))}
            result["fx_effective_at"] = rate.effective_at.isoformat()
    return result

# --- SSR (herkese acik sayfalar): /fiyatlar, sitemap, robots -----------------
app.include_router(admin_router)
app.include_router(web_router)