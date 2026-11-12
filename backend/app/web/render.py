"""Jinja2 ortami, filtreler ve ortak sablon baglami."""
from __future__ import annotations

import datetime as dt
import os
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlencode

from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from .. import __version__
from . import queries
from .i18n import t as _t

BASE_DIR = Path(__file__).parent
TEMPLATES = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Statik varlik surumu: tarayici onbellegini guvenle gecersiz kilmak icin.
ASSET_VERSION = "20261112c"

SITE_NAME = "TokenMaliyet"
SITE_URL = os.getenv("SITE_URL", "http://127.0.0.1:8000")
SITE_DESC = ("Yapay zeka API fiyatlari ve token maliyeti hesaplama. OpenAI, Anthropic, Gemini, "
             "DeepSeek ve OpenRouter fiyatlari, tarihli TL karsiligi ve GPU kiralama maliyetleri.")

PROVIDER_LABELS = {
    "openai": "OpenAI",
    "anthropic": "Anthropic",
    "gemini": "Google Gemini",
    "deepseek": "DeepSeek",
    "openrouter": "OpenRouter",
}
CHANNEL_LABELS = {
    "direct": "Dogrudan API",
    "marketplace": "Pazaryeri",
}


def tl(value: float | Decimal | None, decimals: int = 2) -> str:
    """Turkce yerel ayar: 1.234,56"""
    if value is None:
        return "Belirtilmemis"
    q = Decimal(str(value)).quantize(Decimal(10) ** -decimals)
    s = f"{q:,.{decimals}f}"
    return s.replace(",", "\u00a0").replace(".", ",").replace("\u00a0", ".")


def usd(value: float | Decimal | None) -> str:
    return tl(value, 2)


def dt_tr(value: dt.datetime | dt.date | None, with_time: bool = False) -> str:
    if value is None:
        return "Bilinmiyor"
    fmt = "%d.%m.%Y %H:%M" if with_time and isinstance(value, dt.datetime) else "%d.%m.%Y"
    return value.strftime(fmt)


def age_days(value: dt.datetime | None) -> int | None:
    if value is None:
        return None
    now = dt.datetime.now(dt.timezone.utc)
    ref = value if value.tzinfo else value.replace(tzinfo=dt.timezone.utc)
    return (now - ref).days


def freshness(value: dt.datetime | None) -> tuple[str, str]:
    """(etiket, sinif) - durum hem metin hem renkle anlatilir."""
    days = age_days(value)
    if days is None:
        return ("Tarih yok", "badge-neutral")
    if days <= 2:
        return (f"Dogrulandi ({dt_tr(value)})", "badge-ok")
    if days <= queries.STALE_DAYS:
        return (f"Dogrulandi ({dt_tr(value)})", "badge-neutral")
    return (f"Guncelligi gecmis ({days} gun)", "badge-warn")


def money_cell(dim: dict | None, fx_rate: float | None, show_currency: str = "USD") -> str:
    """Hücre metni: kaynak fiyat + birim; TRY isteniyorsa cevrilir."""
    if not dim:
        return "—"
    amount = dim["amount"]
    if show_currency == "TRY" and fx_rate:
        return tl(amount * fx_rate, 2)
    return tl(amount, dim and 4 if amount < 1 else 2)


def dim_label(key: str) -> str:
    """'input' / 'input:peak' -> okunabilir kalem adi."""
    from .queries import DIMENSIONS

    base = key.split(":")[0]
    return DIMENSIONS.get(base, key)


def price_value(dim: dict | None) -> tuple[float | None, str]:
    """Karsilastirilabilir deger + birim.

    Kaynak fiyati per-token ise (OpenRouter) 1M token karsiligina cevrilir; boylece
    tabloda ayni birim kullanilir. Gorsel/istek gibi token disi birimler oldugu gibi kalir.
    """
    if not dim:
        return (None, "")
    unit = dim.get("billing_unit") or ""
    amount = dim.get("amount")
    if amount is None:
        return (None, "")
    if "token" in unit and "1M" not in unit and "1K" not in unit:
        # USD/token -> USD/1M token
        return (amount * 1_000_000, "USD / 1M token")
    if "1K_tokens" in unit:
        return (amount * 1000, "USD / 1M token")
    if "1M_tokens" in unit:
        return (amount, "USD / 1M token")
    return (amount, unit_label(dim))


def freshness_badge(value) -> dict:
    """Tazelik gostergesi: tek kaynak, tum sayfalar ayni kurali kullanir.

    Rapor 3. tur bulgu 9/10: "UPDATED" kolonu her satirda ayni tarihi gosteriyordu
    ve sayfa basligi ile satirlar farkli tarihler tasiyordu.
    Kural: <=24 saat -> yesil nokta + "bugun"; <=48 saat -> sari; sonrasi tarih.
    """
    import datetime as _dt

    if value is None:
        return {"state": "unknown", "label": "Bilinmiyor", "dot": False, "css": "badge-neutral"}
    ref = value if getattr(value, "tzinfo", None) else value.replace(tzinfo=_dt.timezone.utc)
    hours = (_dt.datetime.now(_dt.timezone.utc) - ref).total_seconds() / 3600
    if hours <= 24:
        return {"state": "fresh", "label": "güncel", "dot": True, "css": "badge-ok", "hours": round(hours, 1)}
    if hours <= 48:
        return {"state": "recent", "label": "son 48 saat", "dot": True, "css": "badge-neutral", "hours": round(hours, 1)}
    return {"state": "stale", "label": dt_tr(value), "dot": False, "css": "badge-warn", "hours": round(hours, 1)}


def price_digits(value: float | None) -> int:
    """Inceleme raporu: 1 USD ustunde 2 ondalik, altinda anlamli basamak.

    13,860 gibi uc ondalikli yazim "on uc bin" diye okunuyordu; artik:
      >= 100  -> 2 ondalik (13,86)
      >= 1    -> 2 ondalik (2,89)
      >= 0,1  -> 3 ondalik (0,150)
      >= 0,01 -> 4 ondalik (0,0289)
      altinda -> 6 ondalik (0,000123)
    """
    if value is None:
        return 2
    v = abs(value)
    if v >= 1:
        return 2
    if v >= 0.1:
        return 3
    if v >= 0.01:
        return 4
    return 6


def price_digits_safe(value) -> int:
    """Sablon icinde dogrudan kullanilabilen varyant (None guvenli)."""
    try:
        return price_digits(float(value))
    except (TypeError, ValueError):
        return 2


def price_text(dim: dict | None) -> str:
    value, _unit = price_value(dim)
    if value is None:
        return "Belirtilmemis"
    return tl(value, price_digits(value))


def unit_label(dim: dict | None) -> str:
    if not dim:
        return ""
    unit = dim.get("billing_unit") or ""
    cur = dim.get("currency") or "USD"
    if "1M_tokens" in unit:
        return f"{cur} / 1M token"
    if "1K_tokens" in unit:
        return f"{cur} / 1K token"
    if "1K_requests" in unit:
        return f"{cur} / 1.000 istek"
    if "token" in unit:
        return f"{cur} / token"
    if "image" in unit:
        return f"{cur} / gorsel"
    if "second" in unit:
        return f"{cur} / saniye"
    if "minute" in unit:
        return f"{cur} / dakika"
    if "request" in unit:
        return f"{cur} / istek"
    return unit or cur


def qs(base: dict, **overrides) -> str:
    """Query string kurucusu; bos degerleri atar."""
    merged = {**base, **overrides}
    clean = {k: v for k, v in merged.items() if v not in (None, "", [])}
    return ("?" + urlencode(clean)) if clean else ""


def _pref(value, allowed, default):
    return value if value in allowed else default


def turkce_multiplier() -> dict:
    """Turkce/Ingilizce token carpani - olculmus veriden (tek kaynak)."""
    import json
    from pathlib import Path

    path = Path(__file__).parent / "data" / "turkce_token.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return {
            "ratio": data["totals"]["ratio"],
            "extra_pct": data["totals"]["extra_pct"],
            "range": data.get("range", {}),
            "samples": data.get("sample_count", 0),
        }
    except Exception:  # noqa: BLE001
        return {"ratio": 1.0, "extra_pct": 0, "range": {}, "samples": 0}


def base_context(db: Session, request, **extra) -> dict:
    qp = request.query_params
    currency = _pref((qp.get("currency") or "").upper(), {"USD", "TRY"}, "USD")
    lang = _pref((qp.get("lang") or "").lower(), {"tr", "en"}, "tr")
    # Tercih degistirirken mevcut filtreleri koru (currency/lang haric).
    keep_params = {k: v for k, v in qp.items() if k not in ("currency", "lang")}
    fx = queries.get_fx(db)
    checked = queries.last_checked(db)
    ctx = {
        "site_name": SITE_NAME,
        "site_tagline": "AI API fiyat ve maliyet verisi",
        "asset_version": ASSET_VERSION,
        "site_url": SITE_URL,
        "site_desc": SITE_DESC,
        "version": __version__,
        "last_checked": dt_tr(checked, with_time=True),
        "last_checked_raw": checked,
        "currency": currency,
        "lang": lang,
        "t": lambda key: _t(key, lang),
        "turkce": turkce_multiplier(),
        "keep_params": keep_params,
        "fx_rate": float(fx.rate) if fx else None,
        "fx_date": dt_tr(fx.effective_at) if fx else None,
        "fx_source": fx.source_url if fx else None,
        "provider_labels": PROVIDER_LABELS,
        "channel_labels": CHANNEL_LABELS,
        "footer_providers": queries.providers(db),
        "path": request.url.path,
        "request": request,
        "noindex": False,
        "canonical": SITE_URL + request.url.path,
    }
    ctx.update(extra)
    return ctx


def _tl_dyn(value) -> str:
    """Degerin buyuklugune gore basamak secen TL bicimi (sablonlarda |tl_dyn)."""
    return tl(value, price_digits_safe(value))


def configure() -> None:
    env = TEMPLATES.env
    env.filters["tl"] = tl
    env.filters["usd"] = usd
    env.filters["dt_tr"] = dt_tr
    env.filters["unit_label"] = unit_label
    env.filters["price_digits"] = price_digits
    env.filters["tl_dyn"] = _tl_dyn
    env.filters["price_digits_safe"] = price_digits_safe
    env.filters["price_value"] = price_value
    env.filters["price_text"] = price_text
    env.globals["price_digits"] = price_digits
    env.globals["price_value"] = price_value
    env.globals["price_text"] = price_text
    env.globals["dim_label"] = dim_label
    env.globals["freshness_badge"] = freshness_badge
    env.filters["freshness_badge"] = freshness_badge
    env.globals["tr_str"] = _t
    env.filters["dim_label"] = dim_label
    env.filters["age_days"] = age_days
    env.filters["freshness"] = freshness
    env.globals["qs"] = qs
    env.globals["freshness"] = freshness
    env.globals["unit_label"] = unit_label