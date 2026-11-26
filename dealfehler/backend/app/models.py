"""Datenbankschema der zentralen Deal-Datenbank."""
from __future__ import annotations

import enum
from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


def _enum(e: type[enum.Enum]) -> Enum:
    return Enum(e, native_enum=False, length=32, values_callable=lambda x: [m.value for m in x])


class Role(str, enum.Enum):
    ADMIN = "admin"
    EDITOR = "editor"
    VIEWER = "viewer"


class DealStatus(str, enum.Enum):
    NEW = "neu"
    IN_REVIEW = "in_pruefung"
    VERIFIED = "verifiziert"
    MEDIA = "medien_werden_erstellt"
    APPROVED = "freigegeben"
    SCHEDULED = "geplant"
    PUBLISHED = "veroeffentlicht"
    PRICE_CHANGED = "preis_geaendert"
    EXPIRED = "abgelaufen"
    FAILED = "fehlerhaft"
    REJECTED = "abgelehnt"  # Score < 50 – wird nicht veröffentlicht


class DealType(str, enum.Enum):
    PRICE_ERROR_SUSPECT = "preisfehler_verdacht"
    TOP_DEAL = "top_deal"
    DEAL = "deal"
    COUPON = "gutschein"
    DAILY_DEAL = "tagesangebot"
    LIGHTNING = "blitzangebot"


class Platform(str, enum.Enum):
    INSTAGRAM = "instagram"
    PINTEREST = "pinterest"
    WHATSAPP = "whatsapp"
    TELEGRAM = "telegram"
    WEBSITE = "website"
    NEWSLETTER = "newsletter"


class PublicationStatus(str, enum.Enum):
    DRAFT = "entwurf"
    PENDING_APPROVAL = "wartet_auf_freigabe"  # z.B. WhatsApp manuell
    SCHEDULED = "geplant"
    PUBLISHING = "wird_veroeffentlicht"
    PUBLISHED = "veroeffentlicht"
    PAUSED = "pausiert"
    FAILED = "fehlgeschlagen"
    CANCELLED = "abgebrochen"


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[Role] = mapped_column(_enum(Role), default=Role.VIEWER)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (UniqueConstraint("merchant", "external_id", name="uq_product_merchant_ext"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    merchant: Mapped[str] = mapped_column(String(64), default="amazon_de")
    external_id: Mapped[str] = mapped_column(String(64))  # ASIN / Händler-SKU
    title: Mapped[str] = mapped_column(String(500))
    brand: Mapped[str | None] = mapped_column(String(200))
    category: Mapped[str] = mapped_column(String(64), default="sonstiges", index=True)
    product_url: Mapped[str] = mapped_column(String(1000))
    source: Mapped[str] = mapped_column(String(64))  # keepa | feed | manual | demo
    # Bildquelle: nur eigene/generierte oder lizenzierte Bilder werden in Medien verwendet
    image_url: Mapped[str | None] = mapped_column(String(1000))
    image_license: Mapped[str] = mapped_column(String(32), default="none")  # none|licensed|api_licensed
    rating: Mapped[float | None] = mapped_column(Float)
    review_count: Mapped[int | None] = mapped_column(Integer)
    sales_rank: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    prices: Mapped[list[PricePoint]] = relationship(back_populates="product", cascade="all, delete-orphan")
    deals: Mapped[list[Deal]] = relationship(back_populates="product")


class PricePoint(Base):
    __tablename__ = "price_points"
    __table_args__ = (Index("ix_price_product_time", "product_id", "observed_at"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"))
    price_cents: Mapped[int] = mapped_column(Integer)
    list_price_cents: Mapped[int | None] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(3), default="EUR")
    source: Mapped[str] = mapped_column(String(64))
    available: Mapped[bool] = mapped_column(Boolean, default=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    product: Mapped[Product] = relationship(back_populates="prices")


class Deal(Base):
    __tablename__ = "deals"
    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), index=True)
    slug: Mapped[str] = mapped_column(String(200), unique=True)
    status: Mapped[DealStatus] = mapped_column(_enum(DealStatus), default=DealStatus.NEW, index=True)
    deal_type: Mapped[DealType] = mapped_column(_enum(DealType), default=DealType.DEAL)
    current_price_cents: Mapped[int] = mapped_column(Integer)
    reference_price_cents: Mapped[int | None] = mapped_column(Integer)  # eigener Median-Preis
    reference_kind: Mapped[str | None] = mapped_column(String(32))  # median_90d | lowest_30d | list_price
    discount_pct: Mapped[float | None] = mapped_column(Float)
    score: Mapped[int] = mapped_column(Integer, default=0, index=True)
    score_breakdown: Mapped[dict] = mapped_column(JSON, default=dict)
    priority: Mapped[float] = mapped_column(Float, default=0.0, index=True)
    verification_count: Mapped[int] = mapped_column(Integer, default=0)
    confirmed_price_error: Mapped[bool] = mapped_column(Boolean, default=False)  # nur manuell
    coupon_code: Mapped[str | None] = mapped_column(String(64))
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    price_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    editorial_note: Mapped[str | None] = mapped_column(Text)  # redaktioneller Mehrwert (Website)
    fingerprint: Mapped[str] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    product: Mapped[Product] = relationship(back_populates="deals")
    links: Mapped[list[AffiliateLink]] = relationship(back_populates="deal", cascade="all, delete-orphan")
    media: Mapped[list[MediaAsset]] = relationship(back_populates="deal", cascade="all, delete-orphan")
    publications: Mapped[list[Publication]] = relationship(back_populates="deal", cascade="all, delete-orphan")
    events: Mapped[list[DealEvent]] = relationship(back_populates="deal", cascade="all, delete-orphan")


class DealEvent(Base):
    """Lückenloses Protokoll aller Statuswechsel."""

    __tablename__ = "deal_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    deal_id: Mapped[int] = mapped_column(ForeignKey("deals.id", ondelete="CASCADE"), index=True)
    from_status: Mapped[str | None] = mapped_column(String(32))
    to_status: Mapped[str] = mapped_column(String(32))
    actor: Mapped[str] = mapped_column(String(64))
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    deal: Mapped[Deal] = relationship(back_populates="events")


class AffiliateLink(Base):
    __tablename__ = "affiliate_links"
    __table_args__ = (UniqueConstraint("deal_id", "network", "channel", name="uq_link_deal_net_channel"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    deal_id: Mapped[int] = mapped_column(ForeignKey("deals.id", ondelete="CASCADE"), index=True)
    network: Mapped[str] = mapped_column(String(32))  # amazon | awin | …
    channel: Mapped[str] = mapped_column(String(32), default="default")
    url: Mapped[str] = mapped_column(String(1500))
    tracking_id: Mapped[str | None] = mapped_column(String(64))
    is_valid: Mapped[bool] = mapped_column(Boolean, default=False)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    check_error: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    deal: Mapped[Deal] = relationship(back_populates="links")


class Click(Base):
    __tablename__ = "clicks"
    __table_args__ = (Index("ix_click_time", "created_at"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    link_id: Mapped[int] = mapped_column(ForeignKey("affiliate_links.id", ondelete="CASCADE"), index=True)
    deal_id: Mapped[int] = mapped_column(ForeignKey("deals.id", ondelete="CASCADE"), index=True)
    channel: Mapped[str] = mapped_column(String(32))
    publication_id: Mapped[int | None] = mapped_column(ForeignKey("publications.id", ondelete="SET NULL"))
    visitor_hash: Mapped[str | None] = mapped_column(String(64))  # gesalzener Hash, keine IP gespeichert
    referrer: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Commission(Base):
    """Provisionen aus Partnerprogramm-Berichten (Import, keine erfundenen Zahlen)."""

    __tablename__ = "commissions"
    __table_args__ = (UniqueConstraint("network", "external_ref", name="uq_commission_ref"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    network: Mapped[str] = mapped_column(String(32))
    external_ref: Mapped[str] = mapped_column(String(128))
    tracking_id: Mapped[str | None] = mapped_column(String(64))
    product_external_id: Mapped[str | None] = mapped_column(String(64))
    deal_id: Mapped[int | None] = mapped_column(ForeignKey("deals.id", ondelete="SET NULL"))
    revenue_cents: Mapped[int] = mapped_column(Integer, default=0)
    commission_cents: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(16), default="estimated")  # estimated|confirmed|rejected
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class MediaAsset(Base):
    __tablename__ = "media_assets"
    id: Mapped[int] = mapped_column(primary_key=True)
    deal_id: Mapped[int] = mapped_column(ForeignKey("deals.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(16))  # post | story | pin | reel
    template: Mapped[str] = mapped_column(String(32))
    storage_key: Mapped[str] = mapped_column(String(500))
    public_url: Mapped[str] = mapped_column(String(1000))
    width: Mapped[int] = mapped_column(Integer)
    height: Mapped[int] = mapped_column(Integer)
    license: Mapped[str] = mapped_column(String(32), default="generated")
    price_cents_rendered: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    deal: Mapped[Deal] = relationship(back_populates="media")


class Publication(Base):
    __tablename__ = "publications"
    __table_args__ = (
        UniqueConstraint("platform", "content_hash", name="uq_pub_platform_hash"),
        Index("ix_pub_status_time", "status", "scheduled_at"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    deal_id: Mapped[int] = mapped_column(ForeignKey("deals.id", ondelete="CASCADE"), index=True)
    platform: Mapped[Platform] = mapped_column(_enum(Platform), index=True)
    format: Mapped[str] = mapped_column(String(16), default="post")  # post | story | reel | pin | message
    status: Mapped[PublicationStatus] = mapped_column(_enum(PublicationStatus), default=PublicationStatus.DRAFT)
    caption: Mapped[str] = mapped_column(Text)
    title: Mapped[str | None] = mapped_column(String(200))
    link_url: Mapped[str | None] = mapped_column(String(1500))
    media_id: Mapped[int | None] = mapped_column(ForeignKey("media_assets.id", ondelete="SET NULL"))
    template: Mapped[str | None] = mapped_column(String(32))
    caption_variant: Mapped[str | None] = mapped_column(String(32))
    board: Mapped[str | None] = mapped_column(String(100))
    price_cents_at_creation: Mapped[int] = mapped_column(Integer)
    content_hash: Mapped[str] = mapped_column(String(64))
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    external_id: Mapped[str | None] = mapped_column(String(128))
    external_url: Mapped[str | None] = mapped_column(String(1000))
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str | None] = mapped_column(Text)
    metrics: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    deal: Mapped[Deal] = relationship(back_populates="publications")
    media: Mapped[MediaAsset | None] = relationship()


class PlatformState(Base):
    """Frequenzmanagement + Not-Aus je Plattform."""

    __tablename__ = "platform_states"
    platform: Mapped[str] = mapped_column(String(32), primary_key=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    kill_switch: Mapped[bool] = mapped_column(Boolean, default=False)
    requires_manual_approval: Mapped[bool] = mapped_column(Boolean, default=False)
    daily_limit: Mapped[int] = mapped_column(Integer, default=3)  # aktuelles (eigenes) Limit
    daily_limit_max: Mapped[int] = mapped_column(Integer, default=10)  # Obergrenze für den Ausbau
    ramp_step: Mapped[int] = mapped_column(Integer, default=1)  # Erhöhung pro Woche bei guter Qualität
    last_ramp_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    min_interval_minutes: Mapped[int] = mapped_column(Integer, default=90)
    quiet_hours_start: Mapped[int] = mapped_column(Integer, default=23)  # lokale Stunde
    quiet_hours_end: Mapped[int] = mapped_column(Integer, default=7)
    min_score: Mapped[int] = mapped_column(Integer, default=60)
    repost_cooldown_days: Mapped[int] = mapped_column(Integer, default=14)
    consecutive_errors: Mapped[int] = mapped_column(Integer, default=0)
    max_consecutive_errors: Mapped[int] = mapped_column(Integer, default=3)
    paused_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    pause_reason: Mapped[str | None] = mapped_column(String(500))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class AgentState(Base):
    __tablename__ = "agent_states"
    name: Mapped[str] = mapped_column(String(64), primary_key=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_status: Mapped[str | None] = mapped_column(String(16))
    last_error: Mapped[str | None] = mapped_column(Text)
    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0)
    run_count: Mapped[int] = mapped_column(Integer, default=0)


class AgentRun(Base):
    __tablename__ = "agent_runs"
    id: Mapped[int] = mapped_column(primary_key=True)
    agent: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(16))  # running | ok | error | skipped
    stats: Mapped[dict] = mapped_column(JSON, default=dict)
    error: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ComplianceCheck(Base):
    __tablename__ = "compliance_checks"
    id: Mapped[int] = mapped_column(primary_key=True)
    deal_id: Mapped[int] = mapped_column(ForeignKey("deals.id", ondelete="CASCADE"), index=True)
    publication_id: Mapped[int | None] = mapped_column(ForeignKey("publications.id", ondelete="CASCADE"))
    passed: Mapped[bool] = mapped_column(Boolean)
    issues: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ErrorLog(Base):
    __tablename__ = "error_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(64), index=True)
    level: Mapped[str] = mapped_column(String(16), default="error")
    message: Mapped[str] = mapped_column(Text)
    context: Mapped[dict] = mapped_column(JSON, default=dict)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class CostEntry(Base):
    __tablename__ = "cost_entries"
    id: Mapped[int] = mapped_column(primary_key=True)
    provider: Mapped[str] = mapped_column(String(32), index=True)
    operation: Mapped[str] = mapped_column(String(64))
    units: Mapped[dict] = mapped_column(JSON, default=dict)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class Report(Base):
    __tablename__ = "reports"
    __table_args__ = (UniqueConstraint("kind", "period", name="uq_report_kind_period"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(16))  # daily | monthly | growth
    period: Mapped[str] = mapped_column(String(16))  # 2026-11-25 | 2026-11
    content: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class KVSetting(Base):
    """Laufzeit-Einstellungen + gelernte Gewichte (Lernsystem)."""

    __tablename__ = "kv_settings"
    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[dict | list | int | float | str | bool | None] = mapped_column(JSON)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    actor: Mapped[str] = mapped_column(String(255))
    action: Mapped[str] = mapped_column(String(100))
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
