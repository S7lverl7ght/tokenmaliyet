"""Korumali yonetim alani: dogrulama kuyrugu ve kaynak sagligi.

Kurallar:
- Herkese acik sayfalardan tamamen ayri; robots.txt ile engellenir ve noindex gonderilir.
- Erisim ADMIN_TOKEN ortam degiskeni ile HTTP Basic benzeri oturum cerezi (HttpOnly) uzerinden.
- ADMIN_TOKEN tanimli degilse alan KAPALIDIR (403). Varsayilan parola yoktur.
"""
from __future__ import annotations

import hmac
import logging
import os
from hashlib import sha256

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from ..db import get_session
from ..models import CollectionRun, DataSource, Model, PriceObservation, Provider, VerificationLog
from . import queries
from .render import SITE_URL, TEMPLATES, base_context, configure

router = APIRouter(prefix="/admin", include_in_schema=False)
configure()

logger = logging.getLogger(__name__)

COOKIE = "amm_admin"


# Guvenlik kapisi (rapor 3. tur madde 1): varsayilan anahtar kabul edilmez.
INSECURE_DEFAULTS = {
    "YerelAdmin2026-degistir",
    "change_me",
    "changeme",
    "admin",
    "password",
    "test",
}


def _token() -> str | None:
    value = os.getenv("ADMIN_TOKEN", "").strip()
    if not value:
        return None
    is_prod = os.getenv("APP_ENV", "dev") == "production"
    if is_prod and (value in INSECURE_DEFAULTS or len(value) < 32):
        # Uretimde zayif anahtar: yonetim paneli KAPALI kalir (guvenli varsayilan).
        logger.error(
            "ADMIN_TOKEN zayif/varsayilan (%d karakter). Uretimde en az 32 karakterlik "
            "rastgele bir anahtar gerekir; yonetim paneli devre disi.",
            len(value),
        )
        return None
    return value


def _cookie_value(token: str) -> str:
    return sha256(("amm::" + token).encode()).hexdigest()


def _authorized(request: Request) -> bool:
    token = _token()
    if token is None:
        return False
    supplied = request.cookies.get(COOKIE, "")
    return hmac.compare_digest(supplied, _cookie_value(token))


def _noindex_ctx(db: Session, request: Request, **extra) -> dict:
    ctx = base_context(db, request, noindex=True, **extra)
    ctx["canonical"] = SITE_URL + request.url.path
    return ctx


@router.get("", response_class=HTMLResponse)
def admin_root(request: Request, db: Session = Depends(get_session)):
    if _token() is None:
        return TEMPLATES.TemplateResponse(
            request, "404.html",
            _noindex_ctx(db, request, message="Yonetim alani kapali (ADMIN_TOKEN tanimli degil)."),
            status_code=403,
        )
    if not _authorized(request):
        return RedirectResponse("/admin/login", status_code=303)
    return RedirectResponse("/admin/kuyruk", status_code=303)


@router.get("/login", response_class=HTMLResponse)
def admin_login(request: Request, db: Session = Depends(get_session)):
    if _token() is None:
        return TEMPLATES.TemplateResponse(
            request, "404.html",
            _noindex_ctx(db, request, message="Yonetim alani kapali (ADMIN_TOKEN tanimli degil)."),
            status_code=403,
        )
    return TEMPLATES.TemplateResponse(request, "admin_login.html", _noindex_ctx(db, request))


@router.post("/login")
def admin_login_post(request: Request, token: str = Form(...), db: Session = Depends(get_session)):
    expected = _token()
    if expected is None:
        return RedirectResponse("/admin", status_code=303)
    if not hmac.compare_digest(token, expected):
        return TEMPLATES.TemplateResponse(
            request, "admin_login.html",
            _noindex_ctx(db, request, error="Anahtar hatali."),
            status_code=401,
        )
    response = RedirectResponse("/admin/kuyruk", status_code=303)
    response.set_cookie(COOKIE, _cookie_value(expected), httponly=True, samesite="strict", max_age=8 * 3600)
    return response


@router.post("/logout")
def admin_logout():
    response = RedirectResponse("/admin/login", status_code=303)
    response.delete_cookie(COOKIE)
    return response


def _queue(db: Session) -> list[dict]:
    rows = db.execute(
        select(PriceObservation, Model, Provider)
        .join(Model, Model.id == PriceObservation.model_id)
        .join(Provider, Provider.id == Model.provider_id)
        .where(PriceObservation.status == "pending")
        .order_by(desc(PriceObservation.observed_at))
        .limit(200)
    ).all()
    fails = dict(db.execute(
        select(VerificationLog.observation_id, func.count(VerificationLog.id))
        .where(VerificationLog.result == "fail")
        .group_by(VerificationLog.observation_id)
    ).all())
    return [
        {"id": o.id, "provider": p.name, "model": m.canonical_id, "dimension": o.price_dimension,
         "amount": float(o.amount), "currency": o.currency, "billing_unit": o.billing_unit,
         "observed_at": o.observed_at, "fails": int(fails.get(o.id, 0))}
        for o, m, p in rows
    ]


@router.get("/kuyruk", response_class=HTMLResponse)
def admin_queue(request: Request, db: Session = Depends(get_session), message: str = ""):
    if not _authorized(request):
        return RedirectResponse("/admin/login", status_code=303)

    runs = db.execute(
        select(CollectionRun, DataSource, Provider)
        .join(DataSource, DataSource.id == CollectionRun.source_id)
        .join(Provider, Provider.id == DataSource.provider_id)
        .order_by(desc(CollectionRun.started_at))
        .limit(12)
    ).all()
    statuses = dict(db.execute(
        select(PriceObservation.status, func.count(PriceObservation.id))
        .group_by(PriceObservation.status)
    ).all())

    ctx = _noindex_ctx(
        db, request,
        pending=_queue(db),
        runs=[{"provider": p.name, "started_at": r.started_at, "status": r.status,
               "items_seen": r.items_seen, "error_summary": r.error_summary} for r, d, p in runs],
        approved_count=statuses.get("approved", 0),
        rejected_count=statuses.get("rejected", 0),
        message=message,
    )
    return TEMPLATES.TemplateResponse(request, "admin_queue.html", ctx)


@router.post("/approve")
def admin_approve(request: Request, observation_id: int = Form(..., alias="id"),
                  db: Session = Depends(get_session)):
    if not _authorized(request):
        return RedirectResponse("/admin/login", status_code=303)
    from ..pipeline import approve
    obs = db.get(PriceObservation, observation_id)
    msg = "Kayit bulunamadi."
    if obs is not None and obs.status == "pending":
        ok = approve(db, obs, actor="admin-ui", require_clean_qa=True)
        db.commit()
        msg = "Onaylandi." if ok else "Hata kaydi oldugu icin onaylanmadi."
    return RedirectResponse(f"/admin/kuyruk?message={msg}", status_code=303)


@router.post("/reject")
def admin_reject(request: Request, observation_id: int = Form(..., alias="id"),
                 db: Session = Depends(get_session)):
    if not _authorized(request):
        return RedirectResponse("/admin/login", status_code=303)
    from ..pipeline import reject
    obs = db.get(PriceObservation, observation_id)
    if obs is not None and obs.status == "pending":
        reject(db, obs, actor="admin-ui", reason="Manuel red")
        db.commit()
    return RedirectResponse("/admin/kuyruk?message=Reddedildi.", status_code=303)
