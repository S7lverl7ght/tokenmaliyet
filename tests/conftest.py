from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://ai_maliyet_user:test_password_only@localhost:5432/ai_maliyet_test",
)

import pytest  # noqa: E402

from app.db import Base, SessionLocal, engine  # noqa: E402
from app import models  # noqa: F401,E402


@pytest.fixture(scope="session", autouse=True)
def _schema():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture()
def db():
    from sqlalchemy import text

    with SessionLocal() as session:
        session.execute(text(
            "TRUNCATE verification_logs, price_observations, collection_runs, models, "
            "data_sources, providers, exchange_rates RESTART IDENTITY CASCADE"
        ))
        session.commit()
        yield session
        session.rollback()

@pytest.fixture(scope="session")
def seeded_data(_schema):
    """Web testleri gercek veri sekliyle calissin diye minimal ama gercekci tohum veri.

    Degerler test amacli sabittir; uretim verisi degildir ve arayuzde gosterilen
    sayilar bu fiksturden degil, calisan veritabanindan gelir.
    """
    import datetime as dt
    from decimal import Decimal

    from app.models import DataSource, ExchangeRate, Model, PriceObservation, Provider

    with SessionLocal() as db:
        p1 = Provider(slug="testprov", name="Test Provider", website="https://example.com",
                      pricing_url="https://example.com/pricing")
        p2 = Provider(slug="otherprov", name="Other Provider", website="https://other.example",
                      pricing_url="https://other.example/pricing")
        db.add_all([p1, p2])
        db.flush()
        s1 = DataSource(provider_id=p1.id, label="Test", source_url="https://example.com/pricing",
                        source_type="official_doc", retrieval_method="http_html", sales_channel="direct")
        s2 = DataSource(provider_id=p2.id, label="Other", source_url="https://other.example/pricing",
                        source_type="official_doc", retrieval_method="http_html", sales_channel="marketplace")
        db.add_all([s1, s2])
        db.flush()

        cheap = Model(provider_id=p1.id, canonical_id="cheap-model", display_name="Cheap Model")
        pricey = Model(provider_id=p1.id, canonical_id="pricey-model:batch", display_name="Pricey Model")
        market = Model(provider_id=p2.id, canonical_id="vendor/market-model", display_name="Market Model")
        db.add_all([cheap, pricey, market])
        db.flush()

        now = dt.datetime.now(dt.timezone.utc)
        rows = [
            (cheap, s1, "input", "1.00", "USD/1M_tokens"),
            (cheap, s1, "output", "4.00", "USD/1M_tokens"),
            (cheap, s1, "cache_read", "0.10", "USD/1M_tokens"),
            (pricey, s1, "input", "15.00", "USD/1M_tokens"),
            (pricey, s1, "output", "75.00", "USD/1M_tokens"),
            (market, s2, "input", "0.0000005", "USD/token"),
            (market, s2, "output", "0.000002", "USD/token"),
        ]
        for i, (model, source, dim, amount, unit) in enumerate(rows):
            db.add(PriceObservation(
                model_id=model.id, source_id=source.id, price_dimension=dim,
                amount=Decimal(amount), currency="USD", billing_unit=unit,
                normalized_usd_per_1m=(Decimal(amount) * 1_000_000 if unit == "USD/token" else Decimal(amount)),
                observed_at=now, status="approved", content_hash=f"webfix-{i}",
            ))
        # pending kayit (admin kuyrugu testi icin)
        db.add(PriceObservation(model_id=cheap.id, source_id=s1.id, price_dimension="input",
                                amount=Decimal("2.00"), currency="USD", billing_unit="USD/1M_tokens",
                                observed_at=now, status="pending", content_hash="webfix-pending"))
        db.add(ExchangeRate(base_currency="USD", quote_currency="TRY", rate=Decimal("50.0"),
                            effective_at=now, source_url="https://fx.example"))
        db.commit()
        yield
