from __future__ import annotations

from decimal import Decimal

from app.collectors.base import ParsedPrice, RawSnapshot
from app.pipeline import _hash_key, ingest, validate_observation
from app.models import PriceObservation, Provider


def _price(amount="0.15", dim="input") -> ParsedPrice:
    return ParsedPrice(model_id="test-model", model_display_name="Test Model", price_dimension=dim,
                       amount=Decimal(amount), currency="USD", billing_unit="USD/1M_tokens")


def _snapshot() -> RawSnapshot:
    return RawSnapshot(source_label="Test", source_url="https://example.com/pricing",
                       fetched_at="2026-11-11T10:00:00+00:00", content_hash="abc", snapshot_path="/tmp/x",
                       items=[])


def test_hash_is_stable_and_dimension_sensitive():
    a = _price(), 1, 1
    assert _hash_key(1, 1, _price()) == _hash_key(1, 1, _price())
    assert _hash_key(1, 1, _price()) != _hash_key(1, 1, _price(amount="0.16"))
    assert _hash_key(1, 1, _price()) != _hash_key(1, 1, _price(dim="output"))


def test_ingest_is_idempotent(db):
    provider = Provider(slug="t1", name="T1", website="https://example.com", pricing_url="https://example.com/p")
    db.add(provider)
    db.flush()
    run1, created1 = ingest(db, provider, _snapshot(), [_price()], "official_doc", "http_html", "direct")
    run2, created2 = ingest(db, provider, _snapshot(), [_price()], "official_doc", "http_html", "direct")
    assert created1 == 1
    assert created2 == 0, "ayni icerik ikinci kez yazilmamali"
    assert db.query(PriceObservation).count() == 1
    assert run1.status == "success"


def test_new_observation_stored_when_price_changes(db):
    provider = Provider(slug="t2", name="T2", website="https://example.com", pricing_url="https://example.com/p2")
    db.add(provider)
    db.flush()
    ingest(db, provider, _snapshot(), [_price("0.15")], "official_doc", "http_html", "direct")
    ingest(db, provider, _snapshot(), [_price("0.20")], "official_doc", "http_html", "direct")
    rows = db.query(PriceObservation).all()
    assert len(rows) == 2, "fiyat degisiminde eski satir korunur, yeni satir eklenir"


def test_negative_price_fails_qa(db):
    provider = Provider(slug="t3", name="T3", website="https://example.com", pricing_url="https://example.com/p3")
    db.add(provider)
    db.flush()
    _run, _n = ingest(db, provider, _snapshot(), [_price("-1")], "official_doc", "http_html", "direct")
    obs = db.query(PriceObservation).first()
    obs.observed_at = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
    assert validate_observation(db, obs) is False


def test_zero_price_without_free_marker_fails(db):
    provider = Provider(slug="t4", name="T4", website="https://example.com", pricing_url="https://example.com/p4")
    db.add(provider)
    db.flush()
    ingest(db, provider, _snapshot(), [_price("0")], "official_doc", "http_html", "direct")
    obs = db.query(PriceObservation).filter(PriceObservation.amount == 0).first()
    assert validate_observation(db, obs) is False
