from __future__ import annotations

import datetime as dt
from decimal import Decimal

from sqlalchemy import (
    BigInteger, Boolean, Date, DateTime, ForeignKey, Index, Numeric, String, Text,
    UniqueConstraint, func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from .db import Base

JSONType = JSON().with_variant(JSONB, "postgresql")


def utcnow() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


class Provider(Base):
    __tablename__ = "providers"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    website: Mapped[str | None] = mapped_column(String(512))
    pricing_url: Mapped[str | None] = mapped_column(String(512))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    models: Mapped[list["Model"]] = relationship(back_populates="provider")
    sources: Mapped[list["DataSource"]] = relationship(back_populates="provider")


class DataSource(Base):
    __tablename__ = "data_sources"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    provider_id: Mapped[int] = mapped_column(ForeignKey("providers.id", ondelete="CASCADE"), nullable=False)
    label: Mapped[str] = mapped_column(String(128), nullable=False)
    source_url: Mapped[str] = mapped_column(String(512), nullable=False)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)  # official_api | official_doc
    retrieval_method: Mapped[str] = mapped_column(String(32), nullable=False)  # http_json | http_html
    is_official: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sales_channel: Mapped[str] = mapped_column(String(32), default="direct", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    provider: Mapped[Provider] = relationship(back_populates="sources")

    __table_args__ = (UniqueConstraint("provider_id", "source_url", name="uq_source_provider_url"),)


class Model(Base):
    __tablename__ = "models"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    provider_id: Mapped[int] = mapped_column(ForeignKey("providers.id", ondelete="CASCADE"), nullable=False)
    canonical_id: Mapped[str] = mapped_column(String(160), nullable=False)
    display_name: Mapped[str] = mapped_column(String(160), nullable=False)
    modalities: Mapped[list | None] = mapped_column(JSONType)
    context_window: Mapped[int | None] = mapped_column(BigInteger)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    provider: Mapped[Provider] = relationship(back_populates="models")

    __table_args__ = (UniqueConstraint("provider_id", "canonical_id", name="uq_model_provider_canonical"),)


class CollectionRun(Base):
    __tablename__ = "collection_runs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("data_sources.id", ondelete="CASCADE"), nullable=False)
    started_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    finished_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(16), default="running", nullable=False)  # running|success|partial|failed
    items_seen: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    snapshot_path: Mapped[str | None] = mapped_column(String(1024))
    content_hash: Mapped[str | None] = mapped_column(String(64))
    error_summary: Mapped[str | None] = mapped_column(Text)


class PriceObservation(Base):
    """Immutable price observation. Rows are never updated for price changes; a new row is inserted."""

    __tablename__ = "price_observations"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    model_id: Mapped[int] = mapped_column(ForeignKey("models.id", ondelete="RESTRICT"), nullable=False)
    source_id: Mapped[int] = mapped_column(ForeignKey("data_sources.id", ondelete="RESTRICT"), nullable=False)
    collection_run_id: Mapped[int | None] = mapped_column(ForeignKey("collection_runs.id", ondelete="SET NULL"))

    price_dimension: Mapped[str] = mapped_column(String(32), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(20, 10), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    billing_unit: Mapped[str] = mapped_column(String(64), nullable=False)
    unit_quantity: Mapped[Decimal] = mapped_column(Numeric(20, 4), default=Decimal("1"), nullable=False)
    normalized_usd_per_1m: Mapped[Decimal | None] = mapped_column(Numeric(20, 6))
    tier_label: Mapped[str | None] = mapped_column(String(64))
    peak_period: Mapped[str | None] = mapped_column(String(16))  # peak | off_peak | standard

    observed_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    effective_from: Mapped[dt.date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(16), default="pending", nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    raw_payload: Mapped[dict | None] = mapped_column(JSONType)
    approved_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    approved_by: Mapped[str | None] = mapped_column(String(64))

    model: Mapped[Model] = relationship()
    source: Mapped[DataSource] = relationship()

    __table_args__ = (
        Index("ix_price_lookup", "model_id", "status", "price_dimension"),
        Index("ix_price_observed", "observed_at"),
    )


class VerificationLog(Base):
    __tablename__ = "verification_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    observation_id: Mapped[int] = mapped_column(
        ForeignKey("price_observations.id", ondelete="CASCADE"), nullable=False
    )
    check_name: Mapped[str] = mapped_column(String(64), nullable=False)
    result: Mapped[str] = mapped_column(String(8), nullable=False)  # pass | fail | warn
    details: Mapped[dict | None] = mapped_column(JSONType)
    checked_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class ExchangeRate(Base):
    __tablename__ = "exchange_rates"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    base_currency: Mapped[str] = mapped_column(String(3), nullable=False)
    quote_currency: Mapped[str] = mapped_column(String(3), nullable=False)
    rate: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    effective_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(512))

    __table_args__ = (UniqueConstraint("base_currency", "quote_currency", "effective_at", name="uq_fx"),)

"""GPU kiralama kaynaklari icin modeller.

Token fiyatlarindan AYRI tutulur: birim GPU-saat, vergi/minimum kiralama farkli.
"""
class GpuProvider(Base):
    """GPU kiralama saglayicisi (Runpod, Vast.ai, ...)."""

    __tablename__ = "gpu_providers"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    website: Mapped[str] = mapped_column(String(512), nullable=False)
    pricing_url: Mapped[str] = mapped_column(String(512), nullable=False)
    kind: Mapped[str] = mapped_column(String(32), default="cloud", nullable=False)  # cloud | marketplace
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class GpuPrice(Base):
    """GPU-saat fiyat gozlemi. Fiyat degisince eski satir korunur, yenisi eklenir."""

    __tablename__ = "gpu_prices"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    provider_id: Mapped[int] = mapped_column(ForeignKey("gpu_providers.id", ondelete="CASCADE"), nullable=False)

    gpu_model: Mapped[str] = mapped_column(String(96), nullable=False)      # H100 SXM, RTX 4090, B200
    gpu_family: Mapped[str] = mapped_column(String(24), nullable=False)     # H100 | A100 | RTX40 | B200
    vram_gb: Mapped[int | None] = mapped_column(BigInteger)
    gpu_count: Mapped[int] = mapped_column(BigInteger, default=1, nullable=False)

    price_per_hour: Mapped[Decimal] = mapped_column(Numeric(14, 6), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    price_kind: Mapped[str] = mapped_column(String(16), default="on_demand", nullable=False)  # on_demand|spot|community|reserved
    min_lease_hours: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    region: Mapped[str | None] = mapped_column(String(96))

    source_url: Mapped[str] = mapped_column(String(512), nullable=False)
    observed_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="pending", nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    raw_payload: Mapped[dict | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)

    provider: Mapped[GpuProvider] = relationship()

    __table_args__ = (
        Index("ix_gpu_lookup", "provider_id", "gpu_family", "status"),
    )

class PriceAlert(Base):
    """Fiyat uyarisi aboneligi (rapor: e-posta listesi + ucretli katmanin ilk urunu).

    KVKK: acik riza metni ve onay zamani saklanir. Cift onay (double opt-in)
    icin token uretilir; onaylanmadan uyari gonderilmez.
    """

    __tablename__ = "price_alerts"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    email: Mapped[str] = mapped_column(String(320), nullable=False, index=True)
    # Takip edilen hedef: provider|model|cikan ya da 'gpu|<family>'
    target: Mapped[str] = mapped_column(String(200), nullable=False)
    target_label: Mapped[str] = mapped_column(String(200), nullable=False)
    direction: Mapped[str] = mapped_column(String(8), default="any", nullable=False)  # up|down|any
    threshold_pct: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=Decimal("10"), nullable=False)

    confirmed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    confirm_token: Mapped[str | None] = mapped_column(String(64), unique=True)
    consent_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    consent_text_version: Mapped[str | None] = mapped_column(String(16))

    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    unsubscribed_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (Index("ix_alert_target", "target", "confirmed"),)
