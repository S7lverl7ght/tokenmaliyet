"""SSR rotalari: herkese acik sayfalar + sitemap/robots."""
from __future__ import annotations

import datetime as dt
import math
import os
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse, Response
from sqlalchemy.orm import Session

from ..db import get_session
from . import default_models as web_defaults
from . import queries
from ..collectors import COLLECTORS
from .render import (PROVIDER_LABELS, SITE_URL, TEMPLATES, base_context, configure,
                     price_value, turkce_multiplier)

router = APIRouter()
configure()

CONTACT_EMAIL = os.getenv("CONTACT_EMAIL", "iletisim@tokenmaliyet.com")

DIM_ORDER = ["input", "output", "cache_read", "cache_write", "image_input", "image_output",
             "audio_input", "audio_output", "request", "second", "gpu_hour"]

SORT_KEYS = {
    "popular": ("popular", False),      # varsayilan: taninmis saglayicilar once
    "input_asc": ("input", False),
    "input_desc": ("input", True),
    "output_asc": ("output", False),
    "output_desc": ("output", True),
    "name_asc": ("name", False),
    "recent": ("recent", True),
}

# Inceleme raporu (11.11.2026): varsayilan gorunumde taninmayan pazaryeri modelleri
# yerine bilinen saglayicilar gorunmeli. Sira: dogrudan saglayicilar -> alfabetik -> fiyat.
POPULAR_PROVIDERS = ["openai", "anthropic", "gemini", "deepseek"]


def _popular_key(r: queries.PriceRow):
    direct = 0 if r.channel == "direct" else 1
    known = 0 if r.provider_slug in POPULAR_PROVIDERS else 1
    price = r.dim("input")
    price_value_ = price.get("usd_per_1m") if price else None
    return (direct, known, price_value_ if price_value_ is not None else float("inf"))


def _filter_sort(rows: list[queries.PriceRow], q: str, provider: str, channel: str, sort: str):
    out = rows
    if provider:
        out = [r for r in out if r.provider_slug == provider]
    if channel:
        out = [r for r in out if r.channel == channel]
    if q:
        needle = q.strip().lower()
        out = [r for r in out if needle in r.name.lower() or needle in r.provider_name.lower()]

    key, reverse = SORT_KEYS.get(sort, SORT_KEYS["popular"])
    if key == "popular":
        out = sorted(out, key=_popular_key)
        return out
    if key == "name":
        out = sorted(out, key=lambda r: r.name.lower(), reverse=reverse)
    elif key == "recent":
        out = sorted(out, key=lambda r: r.observed_at, reverse=True)
    else:
        def price_val(r: queries.PriceRow):
            d = r.dim(key)
            if d is None or d.get("usd_per_1m") is None:
                return float("inf")
            return d["usd_per_1m"]
        out = sorted(out, key=price_val, reverse=reverse)
    return out


def _page_links(page: int, page_count: int) -> list:
    if page_count <= 7:
        return list(range(1, page_count + 1))
    if page <= 4:
        return [1, 2, 3, 4, 5, "…", page_count]
    if page >= page_count - 3:
        return [1, "…"] + list(range(page_count - 4, page_count + 1))
    return [1, "…", page - 1, page, page + 1, "…", page_count]


def _calc_try(amount: float, fx: float | None) -> float | None:
    return amount * fx if fx else None


@router.get("/", include_in_schema=False)
def home():
    return RedirectResponse("/fiyatlar", status_code=302)


@router.get("/fiyatlar", response_class=HTMLResponse, include_in_schema=False)
def prices_page(
    request: Request,
    q: str = "",
    provider: str = "",
    channel: str = "",
    sort: str = "popular",
    page: int = 1,
    db: Session = Depends(get_session),
):
    page_size = 50
    rows = queries.price_rows(db)
    # Inceleme raporu madde 4: alias ('~...-latest') kayitlari varsayilan listede gorunmez.
    visible_rows = [r for r in rows if not r.is_alias]
    filtered = _filter_sort(visible_rows, q, provider, channel, sort)
    page_count = max(1, math.ceil(len(filtered) / page_size))
    requested_page = page
    page = max(1, min(page, page_count))
    start = (page - 1) * page_size
    visible = filtered[start:start + page_size]

    active = []
    if q:
        active.append(f"Arama: {q}")
    if provider:
        active.append(f"Sağlayıcı: {PROVIDER_LABELS.get(provider, provider)}")
    if channel:
        active.append("Kanal: " + ("Doğrudan API" if channel == "direct" else "Pazaryeri"))

    base_q = {"q": q, "provider": provider, "channel": channel, "sort": sort}
    ctx = base_context(
        db, request,
        nav="fiyatlar",
        rows=visible,
        total=len(visible_rows),
        alias_count=len(rows) - len(visible_rows),
        total_filtered=len(filtered),
        provider_count=len({r.provider_slug for r in rows}),
        approved_count=sum(1 for r in rows for _ in r.dims),
        provider_options=queries.providers(db),
        f={"q": q, "provider": provider, "channel": channel, "sort": sort},
        page=page,
        page_size=page_size,
        page_count=page_count,
        page_links=_page_links(page, page_count),
        base_q=base_q,
        active_filters=active,
    )
    ctx["canonical"] = SITE_URL + "/fiyatlar"
    # Filtre kombinasyonlari indekslenmesin (kilavuz: ince/tekrarlanan URL kirliligi).
    # Kilavuz: filtre/sayfa parametreleri indekslenmesin. Istenen sayfa (kisitlanmadan once)
    # esas alinir; aksi halde olmayan sayfa istegi indekslenebilir gorunur.
    ctx["noindex"] = bool(q or provider or channel or sort != "popular" or requested_page > 1)
    return TEMPLATES.TemplateResponse(request, "prices.html", ctx)




@router.get("/modeller/{provider_slug}/{slug:path}", response_class=HTMLResponse, include_in_schema=False)
def model_page(provider_slug: str, slug: str, request: Request, db: Session = Depends(get_session)):
    variants = queries.variants_for(db, provider_slug, slug)
    if not variants:
        return TEMPLATES.TemplateResponse(
            request, "404.html",
            base_context(db, request, nav="fiyatlar", noindex=True,
                         message="Bu model bulunamadı veya yayından kaldırılmış olabilir."),
            status_code=404,
        )
    variants.sort(key=lambda r: (r.variant or ""))
    primary = variants[0]
    dims = sorted(primary.dims.items(), key=lambda kv: DIM_ORDER.index(kv[0]) if kv[0] in DIM_ORDER else 99)
    history_rows = queries.history(db, primary.model_id)[:12]

    # Benzer modeller: ayni saglayicida, girdi fiyati en yakin 5 model
    base_val = price_value(primary.dim("input"))[0]
    pool = [r for r in queries.price_rows(db, provider_slug=provider_slug)
            if r.slug != slug and r.has_tokens]
    if base_val is not None:
        def _dist(r):
            v = price_value(r.dim("input"))[0]
            return abs(v - base_val) if v is not None else float("inf")
        pool.sort(key=_dist)
    similar = pool[:5]

    labels = queries.DIMENSIONS
    ctx = base_context(
        db, request, nav="fiyatlar",
        primary=primary,
        variants=variants,
        provider_label=PROVIDER_LABELS.get(primary.provider_slug, primary.provider_name),
        dimension_labels=labels,
        dims=dims,
        history_rows=history_rows,
        similar=similar,
    )
    ctx["canonical"] = f"{SITE_URL}/modeller/{primary.provider_slug}/{primary.slug}"
    return TEMPLATES.TemplateResponse(request, "model.html", ctx)




def _parse_tokens(raw: str) -> tuple[int | None, str | None]:
    """Turkce binlik ayracli girdiyi (100.000.000) guvenli bicimde sayiya cevirir."""
    if raw is None or str(raw).strip() == "":
        return (0, None)
    cleaned = str(raw).strip().replace(" ", "").replace(".", "").replace(",", ".")
    try:
        value = float(cleaned)
    except ValueError:
        return (None, "Sayi girin. Ornek: 100000000 veya 100.000.000")
    if value < 0:
        return (None, "Negatif token olamaz.")
    if value > 1_000_000_000_000:
        return (None, "Cok buyuk bir deger girdiniz.")
    return (int(value), None)


def _model_options(rows: list[queries.PriceRow], direct_only: bool = False) -> list[dict]:
    """Secenek listesi.

    Ilk HTML'de yalnizca dogrudan saglayici modelleri gomulur (kucuk sayfa, hizli LCP).
    Tam liste (/api/v1/model-options) JavaScript ile yuklenip seceneklere eklenir;
    JS kapaliysa uygulama yine dogrudan API modelleriyle calisir.
    """
    options = []
    pool = [x for x in rows if x.has_tokens and (x.channel == "direct" or not direct_only)]
    for r in sorted(pool, key=lambda x: (x.provider_slug, x.name)):
        label = f"{PROVIDER_LABELS.get(r.provider_slug, r.provider_slug)} · {r.name}"
        if r.variant:
            label += f" ({r.variant})"
        pin = price_value(r.dim("input"))[0]
        pout = price_value(r.dim("output"))[0]
        options.append({
            "value": f"{r.provider_slug}|{r.slug}|{r.variant or ''}",
            "label": label,
            "group": r.channel,
            "input_price": pin,
            "output_price": pout,
        })
    return options


def _find(rows: list[queries.PriceRow], key: str) -> queries.PriceRow | None:
    provider_slug, _, rest = (key or "").partition("|")
    slug, _, variant = rest.partition("|")
    for r in rows:
        if r.provider_slug == provider_slug and r.slug == slug and (r.variant or "") == variant:
            return r
    return None


# Inceleme raporu: bos forma bakan kullaniciyi hizli sonuca goturen hazir senaryolar.
SCENARIOS = [
    {"label": "Destek botu (küçük)", "inp": "45000000", "out": "12000000",
     "note": "Günde ~2.000 sohbet, sohbet başına 750 girdi + 200 çıktı token"},
    {"label": "Kod asistanı", "inp": "90000000", "out": "27000000",
     "note": "10 geliştirici, günde ~300 istek, uzun bağlam"},
    {"label": "Doküman özetleme", "inp": "180000000", "out": "24000000",
     "note": "Günde 500 dosya, uzun girdi ve kısa çıktı"},
    {"label": "İçerik üretimi", "inp": "24000000", "out": "48000000",
     "note": "Günde 200 blog yazısı, kısa girdi ve uzun çıktı"},
    {"label": "RAG / arama", "inp": "300000000", "out": "15000000",
     "note": "Günde 10.000 sorgu, 5 belge bağlamı"},
]


@router.get("/hesaplayici", response_class=HTMLResponse, include_in_schema=False)
def calculator_page(
    request: Request,
    source: str = Query("", alias="from"),
    target: str = Query("", alias="to"),
    tokens_in: str = Query("100000000", alias="in"),
    tokens_out: str = Query("25000000", alias="out"),
    cache: str = Query("0"),
    dil: str = Query("tr"),
    db: Session = Depends(get_session),
):
    rows = queries.price_rows(db)
    options = _model_options(rows, direct_only=True)
    if not options:
        return TEMPLATES.TemplateResponse(request, "404.html",
            base_context(db, request, nav="hesaplayici", noindex=True,
                         message="Henuz hesaplanabilir model fiyati yok."), status_code=404)

    # Varsayilanlar tek kaynaktan (defaults.py) - inceleme raporu madde 7.
    _primary = web_defaults.pick(rows, web_defaults.PREFERRED_PRIMARY)
    _alt = web_defaults.pick(rows, web_defaults.PREFERRED_ALTERNATIVE)
    default_from = web_defaults.key(_primary) if _primary else options[0]["value"]
    default_to = web_defaults.key(_alt) if _alt else options[min(1, len(options) - 1)]["value"]
    source = source or default_from
    target = target or default_to

    errors: dict[str, str] = {}
    n_in, err_in = _parse_tokens(tokens_in)
    n_out, err_out = _parse_tokens(tokens_out)
    if err_in:
        errors["in"] = err_in
    if err_out:
        errors["out"] = err_out

    a = _find(rows, source)
    b = _find(rows, target)
    result = None
    try:
        cache_share = max(0.0, min(0.95, float(cache or 0) / 100))
    except ValueError:
        cache_share = 0.0

    # Turkce token carpani: ayni icerik Turkce'de daha fazla token harcar.
    # Inceleme raporu: bu carpan hesaplayiciya girsin (olculmus: ~2,3x).
    tr_mult = 1.0
    if (dil or "").lower() == "tr":
        tr_mult = float(turkce_multiplier().get("ratio") or 1.0)

    def _cost(row, fa: float, oa: float, mult: float = 1.0) -> float:
        """Girdi maliyeti; cache orani verildiyse o kisim onbellek fiyatindan hesaplanir."""
        cached_price = price_value(row.dim("cache_read"))[0]
        if cache_share > 0 and cached_price is not None:
            direct_share = 1 - cache_share
            per_m_input = fa * direct_share + cached_price * cache_share
        else:
            per_m_input = fa
        return ((n_in * mult) / 1_000_000) * per_m_input + ((n_out * mult) / 1_000_000) * oa

    if not errors and a is not None and b is not None:
        fa = price_value(a.dim("input"))
        oa = price_value(a.dim("output"))
        fb = price_value(b.dim("input"))
        ob = price_value(b.dim("output"))
        if None not in (fa[0], oa[0], fb[0], ob[0]) and n_in is not None and n_out is not None:
            fx = float(queries.get_fx(db).rate) if queries.get_fx(db) else None
            cost_a = _cost(a, fa[0], oa[0], 1.0)
            cost_b = _cost(b, fb[0], ob[0], tr_mult)
            diff = cost_a - cost_b
            pct = (diff / cost_a * 100) if cost_a else None
            result = {
                "from_name": a.name, "to_name": b.name,
                "from_usd": cost_a, "to_usd": cost_b,
                "from_try": cost_a * fx if fx else None,
                "to_try": cost_b * fx if fx else None,
                "diff_usd": diff, "diff_try": diff * fx if fx else None,
                "year_diff_try": diff * fx * 12 if fx else None,
                "pct": pct, "saving": diff > 0,
                "from_in": fa[0], "from_out": oa[0], "to_in": fb[0], "to_out": ob[0],
                "to_bar": round(min(100.0, (cost_b / cost_a * 100) if cost_a else 100), 1),
                "cache_share": round(cache_share * 100),
                "tr_mult": tr_mult,
                "dil": dil,
                "cache_used": cache_share > 0 and price_value(a.dim("cache_read"))[0] is not None,
            }

    ctx = base_context(
        db, request, nav="hesaplayici",
        options=options,
        f={"from": source, "to": target, "in": tokens_in, "out": tokens_out,
           "cache": cache, "dil": dil},
        errors=errors,
        result=result,
        scenarios=SCENARIOS,
    )
    ctx["canonical"] = SITE_URL + "/hesaplayici"
    ctx["noindex"] = bool(source or target or tokens_in != "100000000" or tokens_out != "25000000"
                          or cache != "0" or dil != "tr")
    return TEMPLATES.TemplateResponse(request, "calculator.html", ctx)




@router.get("/karsilastir", response_class=HTMLResponse, include_in_schema=False)
def compare_page(
    request: Request,
    models: list[str] = Query(default=[]),
    tokens_in: str = Query("100000000", alias="in"),
    tokens_out: str = Query("25000000", alias="out"),
    db: Session = Depends(get_session),
):
    rows = queries.price_rows(db)
    options = _model_options(rows, direct_only=True)
    chosen = [m for m in models if m][:4]
    error = None
    cards: list[dict] = []

    # Inceleme raporu: sayfa bos acilmasin. Iki farkli bilinen model varsayilan secilir,
    # boylece kullanici acilista ornek sonucu gorur. 3. ve 4. secici bos kalir.
    if not chosen:
        # Iki farkli, bilinen model varsayilan secilir: sayfa bos acilmasin.
        # Once taninmis modeller denenir; yoksa en ucuz iki dogrudan model kullanilir.
        defaults: list[str] = []
        for needle_set in (web_defaults.PREFERRED_PRIMARY, web_defaults.PREFERRED_ALTERNATIVE):
            row = web_defaults.pick(rows, needle_set)
            if row is not None:
                k = web_defaults.key(row)
                if k not in defaults:
                    defaults.append(k)
        if len(defaults) < 2:
            # Yedek secim: once farkli saglayicilardan, yetmezse ayni saglayicidan devam et.
            candidates = sorted(
                (r for r in rows if r.has_tokens and r.channel == "direct"),
                key=lambda r: (price_value(r.dim("input"))[0] or 0),
            )
            picked: list[str] = []
            for r in candidates:
                key = f"{r.provider_slug}|{r.slug}|{r.variant or ''}"
                if key in picked or key in defaults:
                    continue
                picked.append(key)
                if len(picked) >= 2:
                    break
            # Bilinen modellerden gelenleri koru, eksigi yedekten tamamla.
            for key in picked:
                if len(set(defaults)) >= 2:
                    break
                if key not in defaults:
                    defaults.append(key)
        chosen = list(dict.fromkeys(defaults))[:2]

    n_in, err_in = _parse_tokens(tokens_in)
    n_out, err_out = _parse_tokens(tokens_out)
    if err_in or err_out:
        error = err_in or err_out

    fx = queries.get_fx(db)
    fx_rate = float(fx.rate) if fx else None

    if len(chosen) < 2:
        if chosen:
            error = "En az iki model seçin."
    elif not error:
        picked = []
        for key in chosen:
            row = _find(rows, key)
            if row is not None and row.has_tokens:
                picked.append(row)
        if len(picked) < 2:
            error = "Seçilen modellerden en az biri için girdi/çıktı fiyatı bulunamadı."
        else:
            costs = []
            for row in picked:
                fa = price_value(row.dim("input"))[0]
                oa = price_value(row.dim("output"))[0]
                if fa is None or oa is None:
                    continue
                cost = (n_in / 1_000_000) * fa + (n_out / 1_000_000) * oa
                costs.append((row, fa, oa, cost))
            if costs:
                cheapest = min(c[3] for c in costs)
                top = max(c[3] for c in costs) or 1.0
                for row, fa, oa, cost in costs:
                    cards.append({
                        "name": row.name, "provider_slug": row.provider_slug, "slug": row.slug,
                        "provider_label": PROVIDER_LABELS.get(row.provider_slug, row.provider_name),
                        "channel_label": "Doğrudan API" if row.channel == "direct" else "Pazaryeri",
                        "in_price": fa, "out_price": oa,
                        "month_usd": cost, "month_try": cost * fx_rate if fx_rate else None,
                        "diff_try": (cost - cheapest) * fx_rate if fx_rate else None,
                        "bar_pct": max(4, min(100, cost / top * 100)),
                        "best": abs(cost - cheapest) < 1e-9,
                        "observed": row.observed_at,
                    })
                cards.sort(key=lambda c: c["month_usd"])

    ctx = base_context(
        db, request, nav="karsilastir",
        options=options, selected=chosen, cards=cards, error=error,
        f={"from": "", "to": "", "in": tokens_in, "out": tokens_out},
    )
    ctx["canonical"] = SITE_URL + "/karsilastir"
    ctx["noindex"] = bool(chosen)
    return TEMPLATES.TemplateResponse(request, "compare.html", ctx)




@router.get("/hakkinda", response_class=HTMLResponse, include_in_schema=False)
def about_page(request: Request, db: Session = Depends(get_session)):
    from ..models import DataSource, PriceObservation
    from sqlalchemy import func as sqlfunc, select as sselect
    method_labels = {"http_json": "Resmî JSON API", "http_html": "Resmî fiyat sayfası (HTML)"}
    src_rows = db.execute(
        sselect(DataSource).where(DataSource.is_official.is_(True)).order_by(DataSource.provider_id)
    ).scalars().all()
    by_provider = {p.id: p for p in queries.providers(db)}

    # Inceleme raporu: ayni saglayici iki satirda gorunuyordu (tekrar gibi).
    # Cozum: saglayici basina TEK satir; kullanilan kaynak birincil, digeri "yedek".
    used_urls = {cls.source_url.rstrip("/") for cls in COLLECTORS.values()}
    grouped: dict[int, dict] = {}
    for s in src_rows:
        prov = by_provider.get(s.provider_id)
        if prov is None:
            continue
        entry = grouped.setdefault(prov.id, {
            "name": prov.name, "primary": None, "extra": [],
        })
        item = {
            "url": s.source_url,
            "method": method_labels.get(s.retrieval_method, s.retrieval_method),
        }
        is_used = s.source_url.rstrip("/") in used_urls
        if is_used and entry["primary"] is None:
            entry["primary"] = item
        elif entry["primary"] is None:
            entry["primary"] = item
        else:
            entry["extra"].append(item)
    sources = [
        {"name": e["name"], "pricing_url": e["primary"]["url"], "method": e["primary"]["method"],
         "extra": e["extra"]}
        for e in grouped.values()
    ]
    observation_count = db.scalar(
        sselect(sqlfunc.count(PriceObservation.id)).where(PriceObservation.status == queries.APPROVED)
    ) or 0
    from ..models import GpuPrice
    gpu_count = db.scalar(sselect(sqlfunc.count(GpuPrice.id)).where(GpuPrice.status == "approved")) or 0
    ctx = base_context(db, request, nav="hakkinda", sources=sources,
                       observation_count=observation_count, gpu_count=gpu_count,
                       contact_email=CONTACT_EMAIL, stale_days=queries.STALE_DAYS)
    ctx["canonical"] = SITE_URL + "/hakkinda"
    return TEMPLATES.TemplateResponse(request, "about.html", ctx)




@router.get("/rehber", response_class=HTMLResponse, include_in_schema=False)
def guide_index(request: Request, db: Session = Depends(get_session)):
    from .content.guides import GUIDES
    ctx = base_context(db, request, nav="rehber", guides=GUIDES)
    ctx["canonical"] = SITE_URL + "/rehber"
    return TEMPLATES.TemplateResponse(request, "guide_index.html", ctx)


@router.get("/rehber/{slug}", response_class=HTMLResponse, include_in_schema=False)
def guide_page(slug: str, request: Request, db: Session = Depends(get_session)):
    from .content.guides import GUIDES, by_slug
    guide = by_slug(slug)
    if guide is None:
        return TEMPLATES.TemplateResponse(
            request, "404.html",
            base_context(db, request, nav="rehber", noindex=True,
                         message="Bu rehber yazisi bulunamadi."),
            status_code=404,
        )
    others = [g for g in GUIDES if g.slug != slug][:3]

    # Ornek tablolar gercek veriden uretilir; elle yazilmis fiyat yok.
    rows = queries.price_rows(db)
    examples = []
    for needle in ("claude-sonnet-4.5", "deepseek-v4-pro", "gpt-6-luna"):
        row = next((r for r in rows if r.name == needle and r.has_tokens), None)
        if row:
            examples.append({
                "name": row.name,
                "input": price_value(row.dim("input"))[0],
                "output": price_value(row.dim("output"))[0],
            })

    peak_examples = []
    for r in rows:
        if r.name.startswith("deepseek") and "input" in r.dims:
            d = r.dims["input"]
            if d.get("peak_period") in ("peak", "off_peak"):
                peak_examples.append({
                    "model": r.name,
                    "dimension": "Girdi (input)",
                    "period": "Yoğun saat" if d["peak_period"] == "peak" else "Yoğun olmayan saat",
                    "price": price_value(d)[0],
                })
    peak_examples.sort(key=lambda x: (x["model"], x["period"]))

    ctx = base_context(db, request, nav="rehber", guide=guide, other_guides=others,
                       examples=examples, peak_examples=peak_examples)
    ctx["canonical"] = f"{SITE_URL}/rehber/{slug}"
    ctx["noindex"] = False
    template = f"rehber/{slug}.html"
    return TEMPLATES.TemplateResponse(request, template, ctx)




@router.get("/api/v1/model-options", include_in_schema=False)
def model_options_json(db: Session = Depends(get_session)) -> list[dict]:
    """Hesaplayici/karistirma icin tam model listesi (kucuk JSON, onbelleklenebilir)."""
    return _model_options(queries.price_rows(db))


@router.get("/token-sayaci", response_class=HTMLResponse, include_in_schema=False)
def token_counter(request: Request, db: Session = Depends(get_session)):
    rows = queries.price_rows(db)
    options = _model_options(rows, direct_only=True)
    _counter = web_defaults.pick(rows, web_defaults.PREFERRED_COUNTER)
    ctx = base_context(db, request, nav="token", options=options,
                       default_model=web_defaults.key(_counter) if _counter else "")
    ctx["canonical"] = SITE_URL + "/token-sayaci"
    return TEMPLATES.TemplateResponse(request, "token_sayaci.html", ctx)


@router.get("/gpu-maliyetleri", response_class=HTMLResponse, include_in_schema=False)
def gpu_page(request: Request, db: Session = Depends(get_session)):
    from sqlalchemy import func as sqlfunc, select as sselect
    from ..models import GpuPrice, GpuProvider

    # Saglayici + GPU ailesi bazinda en iyi (en dusuk on-demand) fiyat
    rows = db.execute(
        sselect(GpuPrice, GpuProvider)
        .join(GpuProvider, GpuProvider.id == GpuPrice.provider_id)
        .where(GpuPrice.status == "approved")
        .order_by(GpuPrice.price_per_hour)
    ).all()

    fam_map: dict[str, dict] = {}
    prov_map: dict[str, dict] = {}
    for price, provider in rows:
        key = price.gpu_family
        entry = fam_map.setdefault(key, {
            "family": key, "vram": price.vram_gb, "best": None, "offers": [],
            "kinds": set(),
        })
        entry["offers"].append({
            "provider": provider.name, "provider_slug": provider.slug,
            "gpu_model": price.gpu_model, "price": float(price.price_per_hour),
            "kind": price.price_kind, "vram": price.vram_gb, "url": provider.pricing_url,
            "min_lease": float(price.min_lease_hours) if price.min_lease_hours else None,
            "observed": price.observed_at,
        })
        entry["kinds"].add(price.price_kind)
        # Varsayilan karsilastirma ON-DEMAND fiyatidir: aninda acilir ve karsilastirilabilir.
        # Spot/topluluk fiyatlari ayri gosterilir; tek bir ucuz aykiri deger tabloyu ele gecirmesin.
        if price.price_kind == "on_demand":
            if entry["best"] is None or float(price.price_per_hour) < entry["best"]["price"]:
                entry["best"] = entry["offers"][-1]
        if price.vram_gb and not entry["vram"]:
            entry["vram"] = price.vram_gb

        pe = prov_map.setdefault(provider.slug, {
            "name": provider.name, "slug": provider.slug, "url": provider.pricing_url,
            "kind": provider.kind, "count": 0, "min": None, "max": None,
        })
        pe["count"] += 1
        value = float(price.price_per_hour)
        pe["min"] = value if pe["min"] is None else min(pe["min"], value)
        pe["max"] = value if pe["max"] is None else max(pe["max"], value)

    families = []
    for entry in fam_map.values():
        offers = sorted(entry["offers"], key=lambda o: o["price"])
        on_demand = [o for o in offers if o["kind"] == "on_demand"]
        best = entry["best"] or (on_demand[0] if on_demand else offers[0])
        shown = offers[:6]
        # Inceleme raporu madde 1: aralik GOSTERILEN satirlardan hesaplanir.
        # Once 13,260 gibi listede olmayan bir ust deger gorunuyordu (tutarsizlik).
        shown_prices = [o["price"] for o in shown] + [best["price"]]
        families.append({
            "family": entry["family"],
            "vram": entry["vram"],
            "best": best,
            "offers": shown,
            "count": len(offers),
            "max": max(shown_prices),
            "cheapest_any": offers[0],
            "has_discount": bool(on_demand) and offers[0]["kind"] != "on_demand",
        })
    # VRAM buyukten kucuge, sonra fiyat
    families.sort(key=lambda f: (-(f["vram"] or 0), f["best"]["price"]))

    providers = sorted(prov_map.values(), key=lambda p: p["name"])
    total = sum(p["count"] for p in providers)
    ctx = base_context(
        db, request, nav="gpu",
        families=families,
        providers=providers,
        gpu_count=total,
        has_gpu=bool(families),
    )
    ctx["canonical"] = SITE_URL + "/gpu-maliyetleri"
    return TEMPLATES.TemplateResponse(request, "gpu.html", ctx)




# Inceleme raporu (11.11.2026): yayimlanmis duzeltmeler kamuya acik olsun.
CORRECTIONS: list[dict] = [
    {
        "date": "11.11.2026",
        "item": "z-ai/glm-5.2, deepseek-v4.1-flash, kimi-k3 (OpenRouter)",
        "old": "girdi 0,0000000070 USD/token",
        "new": "yayından kaldırıldı",
        "reason": "Çıktı/girdi oranı 971x — kaynakta birim hatası; doğrulanana kadar yayınlanmıyor",
    },
    {
        "date": "11.11.2026",
        "item": "Tüm fiyat tablosu",
        "old": "13,860 USD",
        "new": "13,86 USD",
        "reason": "Üç ondalık yazım on üç bin diye okunuyordu; basamak sayısı değere göre uyarlandı",
    },
]


def _legal(db, request, template: str, title: str, desc: str, **extra):
    ctx = base_context(db, request, nav="legal", page_title=title, page_desc=desc,
                       contact_email=CONTACT_EMAIL, **extra)
    ctx["canonical"] = SITE_URL + request.url.path
    return TEMPLATES.TemplateResponse(request, template, ctx)


@router.get("/gizlilik", response_class=HTMLResponse, include_in_schema=False)
def privacy_page(request: Request, db: Session = Depends(get_session)):
    return _legal(db, request, "legal_privacy.html", "Gizlilik ve KVKK aydınlatma",
                  "Hangi veriler işleniyor, çerez kullanımı, KVKK kapsamındaki haklarınız ve sorumluluk reddi.")


@router.get("/iletisim", response_class=HTMLResponse, include_in_schema=False)
def contact_page(request: Request, db: Session = Depends(get_session)):
    return _legal(db, request, "legal_contact.html", "İletişim",
                  "Veri düzeltmesi, hatalı fiyat bildirimi ve iş birliği için iletişim.")


@router.get("/duzeltmeler", response_class=HTMLResponse, include_in_schema=False)
def corrections_page(request: Request, db: Session = Depends(get_session)):
    return _legal(db, request, "legal_corrections.html", "Düzeltmeler",
                  "Yayımlanmış fiyat düzeltmelerinin kamuya açık kaydı: eski değer, yeni değer ve gerekçe.",
                  corrections=CORRECTIONS)




def _turkce_data() -> dict:
    """Turkce/Ingilizce token olcum verisi (gercek tokenizer ile uretildi)."""
    import json
    from pathlib import Path

    path = Path(__file__).parent / "data" / "turkce_token.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {"encoding": "-", "samples": [],
                "totals": {"tr_tokens": 0, "en_tokens": 0, "ratio": 1, "extra_pct": 0},
                "efficiency": {"tr_chars_per_token": 0, "en_chars_per_token": 0}}


@router.get("/turkce-token-maliyeti", response_class=HTMLResponse, include_in_schema=False)
def turkce_token_page(request: Request, db: Session = Depends(get_session)):
    rows = queries.price_rows(db)
    options = _model_options(rows, direct_only=True)
    ctx = base_context(db, request, nav="token", data=_turkce_data(), options=options)
    ctx["canonical"] = SITE_URL + "/turkce-token-maliyeti"
    return TEMPLATES.TemplateResponse(request, "turkce_token.html", ctx)




@router.get("/degisiklikler", response_class=HTMLResponse, include_in_schema=False)
def changes_page(request: Request, days: int = 30, db: Session = Depends(get_session)):
    """Son N gunde fiyati degisen modeller + yayimlanmis duzeltmeler."""
    from sqlalchemy import func as sqlfunc, select as sselect
    from ..models import Model, PriceObservation, Provider

    days = max(1, min(365, days))
    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days)

    rows = db.execute(
        sselect(PriceObservation, Model, Provider)
        .join(Model, Model.id == PriceObservation.model_id)
        .join(Provider, Provider.id == Model.provider_id)
        .where(PriceObservation.status == "approved", PriceObservation.observed_at >= cutoff)
        .order_by(PriceObservation.observed_at.desc())
    ).all()

    # Model + kalem + donem bazinda en eski ve en yeni gozlemi karsilastir
    grouped: dict[tuple, list] = {}
    for obs, model, prov in rows:
        k = (model.id, obs.price_dimension, obs.peak_period, obs.tier_label)
        grouped.setdefault(k, []).append((obs, model, prov))

    changes = []
    for k, items in grouped.items():
        items.sort(key=lambda x: x[0].observed_at)
        first, last = items[0], items[-1]
        old, new = float(first[0].amount), float(last[0].amount)
        if abs(new - old) < 1e-12 or old <= 0:
            continue
        model = last[1]
        from .queries import split_variant, to_slug
        base, _variant = split_variant(model.canonical_id)
        changes.append({
            "model": base, "slug": to_slug(base), "provider": last[2].slug,
            "dimension": last[0].price_dimension,
            "old": old, "new": new,
            "pct": (new - old) / old * 100,
            "date": last[0].observed_at,
        })
    changes.sort(key=lambda c: abs(c["pct"]), reverse=True)

    ctx = base_context(db, request, nav="degisiklikler",
                       changes=changes[:60], corrections=CORRECTIONS, days=days)
    ctx["canonical"] = SITE_URL + "/degisiklikler"
    return TEMPLATES.TemplateResponse(request, "degisiklikler.html", ctx)


@router.get("/robots.txt", response_class=PlainTextResponse, include_in_schema=False)
def robots():
    return ("User-agent: *\n"
            "Allow: /fiyatlar\n"
            "Allow: /modeller/\n"
            "Allow: /karsilastir\n"
            "Allow: /hesaplayici\n"
            "Allow: /gpu-maliyetleri\n"
            "Allow: /rehber\n"
            "Disallow: /admin\n"
            "Disallow: /api/\n"
            "Disallow: /fiyatlar?\n"
            "\n"
            f"Sitemap: {SITE_URL}/sitemap.xml\n")


@router.get("/sitemap.xml", include_in_schema=False)
def sitemap(db: Session = Depends(get_session)) -> Response:
    from .content.guides import GUIDES
    urls = ["/fiyatlar", "/karsilastir", "/hesaplayici", "/token-sayaci",
            "/gpu-maliyetleri", "/rehber", "/hakkinda",
            "/gizlilik", "/iletisim", "/duzeltmeler",
            "/turkce-token-maliyeti", "/degisiklikler"]
    urls += [f"/rehber/{g.slug}" for g in GUIDES]
    seen: set[str] = set()
    for row in queries.price_rows(db):
        if not row.has_tokens:
            continue
        path = f"/modeller/{row.provider_slug}/{row.slug}"
        if path in seen:
            continue
        seen.add(path)
        urls.append(path)

    body = ["<?xml version=\"1.0\" encoding=\"UTF-8\"?>",
            "<urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">"]
    for path in urls:
        body.append(f"<url><loc>{SITE_URL}{path}</loc><changefreq>daily</changefreq></url>")
    body.append("</urlset>")
    return Response("\n".join(body), media_type="application/xml")