from __future__ import annotations

import datetime as dt
from decimal import Decimal

from fastapi.testclient import TestClient

from app.main import app
from app.models import DataSource, Model, PriceObservation, Provider, ExchangeRate


def _seed(db):
    provider = Provider(slug="aprov", name="A Provider", website="https://a.example", pricing_url="https://a.example/p")
    db.add(provider)
    db.flush()
    source = DataSource(provider_id=provider.id, label="A", source_url="https://a.example/p",
                        source_type="official_doc", retrieval_method="http_html", sales_channel="direct")
    db.add(source)
    model = Model(provider_id=provider.id, canonical_id="a-model", display_name="A Model")
    db.add(model)
    db.flush()
    now = dt.datetime.now(dt.timezone.utc)
    for dimension, amount, status in (("input", "1", "approved"), ("output", "2", "approved"),
                                      ("input", "9", "pending"), ("output", "9", "rejected")):
        db.add(PriceObservation(model_id=model.id, source_id=source.id, price_dimension=dimension,
                                amount=Decimal(amount), currency="USD", billing_unit="USD/1M_tokens",
                                observed_at=now, status=status, content_hash=f"h-{dimension}-{status}",
                                normalized_usd_per_1m=Decimal(amount)))
    db.add(ExchangeRate(base_currency="USD", quote_currency="TRY", rate=Decimal("50"), effective_at=now,
                        source_url="https://fx.example"))
    db.commit()
    return model


def test_only_approved_prices_are_published(db):
    _seed(db)
    client = TestClient(app)
    rows = client.get("/api/v1/prices", params={"provider_id": 1}).json()
    assert rows, "approved kayit donmeli"
    assert all(r["amount"] in (1.0, 2.0) for r in rows), "pending/rejected gorunmemeli"


def test_health_and_estimate(db):
    model = _seed(db)
    client = TestClient(app)
    assert client.get("/health").json()["status"] == "ok"
    assert client.get("/health/db").json()["database"] == "connected"
    est = client.get("/api/v1/estimate", params={"model_id": model.id, "input_tokens": 1000000,
                                                 "output_tokens": 0, "quote": "TRY"}).json()
    assert est["usd"] == 1.0
    assert est["converted"]["TRY"] == 50.0
