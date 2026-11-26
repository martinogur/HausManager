"""Duplikaterkennung für Deals und Veröffentlichungen."""
import hashlib
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Publication, PublicationStatus


def deal_fingerprint(merchant: str, external_id: str, price_cents: int) -> str:
    # Preis auf 1-€-Raster, damit Cent-Schwankungen keinen "neuen" Deal erzeugen
    bucket = price_cents // 100
    return hashlib.sha256(f"{merchant}|{external_id}|{bucket}".encode()).hexdigest()[:32]


def content_hash(platform: str, deal_id: int, price_cents: int, fmt: str) -> str:
    return hashlib.sha256(f"{platform}|{deal_id}|{price_cents}|{fmt}".encode()).hexdigest()[:40]


def recently_posted_product(db: Session, platform: str, product_id: int, price_cents: int,
                            cooldown_days: int, t: datetime) -> bool:
    """True, wenn das Produkt im Cooldown schon gepostet wurde und der Preis nicht >5 % besser ist."""
    from app.models import Deal

    rows = db.execute(
        select(Publication.price_cents_at_creation)
        .join(Deal, Deal.id == Publication.deal_id)
        .where(
            Deal.product_id == product_id,
            Publication.platform == platform,
            Publication.status.in_([PublicationStatus.PUBLISHED, PublicationStatus.SCHEDULED,
                                    PublicationStatus.PENDING_APPROVAL, PublicationStatus.PUBLISHING]),
            Publication.created_at >= t - timedelta(days=cooldown_days),
        )
    ).scalars().all()
    return any(price_cents > p * 0.95 for p in rows)
