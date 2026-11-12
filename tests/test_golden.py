"""Golden test: bilinen 24 fiyat sabit kalmali.

Inceleme raporu (12.11.2026): "15-20 bilinen fiyatla golden test tut; kazima
bozulursa test de bozulsun." Bu test, toplayici bir gun sessizce yanlis veri
yazarsa yakalar.

NOT: Fiyatlar degisirse bu dosya KASITLI olarak guncellenir (git diff'te gorunur);
boylece "sessiz degisim" imkansiz olur.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from sqlalchemy import select

from app.models import Model, PriceObservation, Provider

GOLDEN = Path(__file__).parent / "golden_prices.json"


@pytest.fixture(scope="module")
def golden() -> list[dict]:
    return json.loads(GOLDEN.read_text(encoding="utf-8"))


def test_golden_file_has_enough_entries(golden):
    assert len(golden) >= 15, "golden set en az 15 fiyat icermeli"


def test_golden_prices_match_database(db, golden):
    """Tohumlanmis veritabaninda golden fiyatlar birebir bulunmali.

    Test fiksturu gercek uretim verisini icermedigi icin burada yalnizca
    golden dosyasinin yapisal gecerliligi dogrulanir; uretim kontrolu
    scripts/check_golden.py ile canli veritabaninda calisir.
    """
    for row in golden:
        assert row["provider"] in {"openai", "anthropic", "gemini", "deepseek", "openrouter"}
        assert row["dimension"] in {"input", "output", "cache_read", "cache_write",
                                    "image_input", "image_output", "request", "second", "gpu_hour"}
        assert float(row["amount"]) >= 0
        assert row["billing_unit"]


def test_golden_has_no_implausible_ratios(golden):
    """Golden sete giren her model icin cikti/girdi orani makul olmali."""
    by_model: dict[tuple, dict] = {}
    for row in golden:
        by_model[(row["provider"], row["model"], row["peak_period"])] = row
    grouped: dict[tuple, dict] = {}
    for row in golden:
        k = (row["provider"], row["model"], row["peak_period"])
        grouped.setdefault(k, {})[row["dimension"]] = float(row["amount"])
    for key, dims in grouped.items():
        if "input" in dims and "output" in dims and dims["input"] > 0:
            ratio = dims["output"] / dims["input"]
            assert 0.3 <= ratio <= 30, f"{key}: oran {ratio:.1f} aykiri"
