"""Affiliate / referans baglantilari.

Kural: uydurma kod yazilmaz. Kod yalnizca ortam degiskeninde tanimliysa eklenir.
Ortam degiskeni yoksa duz URL doner (mevcut davranis korunur).

Ornek .env:
    AFFILIATE_RUNPOD=ref=abc123
    AFFILIATE_VASTAI=ref=xyz
"""
from __future__ import annotations

import os
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


def _param_for(slug: str) -> str:
    key = "AFFILIATE_" + (slug or "").upper().replace("-", "").replace(".", "")
    return (os.getenv(key) or "").strip()


def with_affiliate(url: str, slug: str) -> str:
    """URL'ye affiliate parametresini ekler; kod yoksa URL aynen doner."""
    param = _param_for(slug)
    if not param or not url:
        return url
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query))
    for k, v in parse_qsl(param):
        query[k] = v
    return urlunsplit((parts.scheme, parts.netloc, parts.path,
                       urlencode(query), parts.fragment))


def is_affiliate(slug: str) -> bool:
    return bool(_param_for(slug))
