"""Öffentliche Endpunkte für die Website (ohne Login)."""
from __future__ import annotations

import hashlib
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.agents.pipeline import deal_label, link_for
from app.api.serializers import iso
from app.config import get_settings
from app.creative.captions import CaptionInput, website_text
from app.db import get_db
from app.domain.compliance import AMAZON_DISCLOSURE
from app.domain.timeutil import aware, fmt_local, now
from app.models import Click, Deal, PricePoint, Product, Publication
from app.models import DealStatus as S
from app.models import PublicationStatus as PS

router = APIRouter(prefix="/api/public")
VISIBLE = [S.PUBLISHED, S.SCHEDULED, S.APPROVED]


def _visible_stmt():
    on_site = select(Publication.deal_id).where(Publication.platform == "website", Publication.status == PS.PUBLISHED)
    return (select(Deal).join(Product)
            .where(Deal.id.in_(on_site), Deal.status.in_(VISIBLE + [S.EXPIRED, S.PRICE_CHANGED])))


def _card(d: Deal) -> dict:
    p = d.product
    media = next((m for m in d.media if m.kind == "post" and m.price_cents_rendered == d.current_price_cents), None)
    active = d.status in VISIBLE
    return {
        "slug": d.slug, "title": p.title, "brand": p.brand, "category": p.category, "label": deal_label(d),
        "deal_type": d.deal_type.value, "price_cents": d.current_price_cents,
        "reference_price_cents": d.reference_price_cents if d.reference_kind == "median_90d" else None,
        "discount_pct": d.discount_pct if d.reference_kind == "median_90d" else None,
        "score": d.score, "active": active, "price_checked_at": iso(d.price_checked_at),
        "price_stand": fmt_local(aware(d.price_checked_at)) if d.price_checked_at else None,
        "image_url": media.public_url if media else None, "created_at": iso(d.created_at),
        "updated_at": iso(d.updated_at),
    }


@router.get("/deals")
def public_deals(category: str | None = None, type: str | None = None, q: str | None = None, page: int = 1,
                 include_expired: bool = False, db: Session = Depends(get_db)):
    stmt = _visible_stmt()
    if not include_expired:
        stmt = stmt.where(Deal.status.in_(VISIBLE))
    if category:
        stmt = stmt.where(Product.category == category)
    if type == "preisfehler":
        stmt = stmt.where(Deal.score >= 90)
    elif type:
        stmt = stmt.where(Deal.deal_type == type)
    if q:
        stmt = stmt.where(Product.title.ilike(f"%{q[:80]}%"))
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = db.scalars(stmt.order_by(Deal.created_at.desc()).limit(24).offset((max(page, 1) - 1) * 24)).all()
    return {"total": total, "page": page, "items": [_card(d) for d in rows], "disclosure": AMAZON_DISCLOSURE}


@router.get("/deals/{slug}")
def public_deal(slug: str, src: str | None = None, db: Session = Depends(get_db)):
    d = db.scalar(_visible_stmt().where(Deal.slug == slug).limit(1))
    if not d:
        raise HTTPException(404, "Deal nicht gefunden")
    lk = link_for(d, src or "website")
    since = now() - timedelta(days=90)
    rows = db.execute(select(func.date(PricePoint.observed_at), func.min(PricePoint.price_cents))
                      .where(PricePoint.product_id == d.product_id, PricePoint.observed_at >= since,
                             PricePoint.available.is_(True), PricePoint.price_cents > 0)
                      .group_by(func.date(PricePoint.observed_at)).order_by(func.date(PricePoint.observed_at))).all()
    card = _card(d)
    ci = CaptionInput(title=d.product.title, price_cents=d.current_price_cents,
                      reference_price_cents=card["reference_price_cents"], discount_pct=card["discount_pct"],
                      label=card["label"], category=d.product.category, price_stand=card["price_stand"] or "",
                      editorial_note=d.editorial_note)
    related = db.scalars(_visible_stmt().where(Deal.status.in_(VISIBLE), Product.category == d.product.category,
                                               Deal.id != d.id).order_by(Deal.created_at.desc()).limit(4)).all()
    return {
        **card, "text": website_text(ci), "editorial_note": d.editorial_note,
        "affiliate_url": lk.url if (lk and card["active"]) else None, "network": lk.network if lk else None,
        "coupon_code": d.coupon_code, "price_history": [{"date": str(day), "price_cents": c} for day, c in rows],
        "reference_explanation": ("Vergleichspreis = Median unserer eigenen Preisbeobachtungen der letzten 90 Tage "
                                  "(ohne die letzten 24 Stunden), nicht die UVP."),
        "disclosure": AMAZON_DISCLOSURE, "related": [_card(r) for r in related],
    }


class ClickIn(BaseModel):
    slug: str = Field(max_length=200)
    src: str | None = Field(None, max_length=32)
    publication_id: int | None = None


ALLOWED_CHANNELS = {"website", "instagram", "pinterest", "telegram", "whatsapp", "newsletter"}


@router.post("/click", status_code=204)
def track_click(body: ClickIn, request: Request, db: Session = Depends(get_db)):
    """Klick-Beacon (navigator.sendBeacon). Der Affiliate-Link selbst bleibt direkt und unverschleiert.
    Datenschutz: Es wird keine IP gespeichert, nur ein täglich wechselnder Hash zur Dublettenerkennung."""
    d = db.scalar(select(Deal).where(Deal.slug == body.slug))
    if not d:
        return None
    channel = body.src if body.src in ALLOWED_CHANNELS else "website"
    lk = link_for(d, channel)
    if not lk:
        return None
    ip = request.client.host if request.client else ""
    day = now().date().isoformat()
    vh = hashlib.sha256(f"{get_settings().secret_key}|{day}|{ip}|{request.headers.get('user-agent', '')}".encode()).hexdigest()
    # Doppelklicks desselben Besuchers innerhalb von 30 s ignorieren
    recent = db.scalar(select(Click.id).where(Click.visitor_hash == vh, Click.deal_id == d.id,
                                              Click.created_at >= now() - timedelta(seconds=30)))
    if recent:
        return None
    pub_id = body.publication_id
    if pub_id is None and channel != "website":
        pub_id = db.scalar(select(Publication.id).where(Publication.deal_id == d.id, Publication.platform == channel,
                                                        Publication.status == PS.PUBLISHED).limit(1))
    db.add(Click(link_id=lk.id, deal_id=d.id, channel=channel, publication_id=pub_id, visitor_hash=vh,
                 referrer=(request.headers.get("referer") or "")[:500]))
    db.commit()
    return None


@router.get("/categories")
def categories(db: Session = Depends(get_db)):
    rows = db.execute(select(Product.category, func.count(func.distinct(Deal.id))).select_from(Deal).join(Product)
                      .join(Publication, Publication.deal_id == Deal.id)
                      .where(Publication.platform == "website", Publication.status == PS.PUBLISHED,
                             Deal.status.in_(VISIBLE)).group_by(Product.category)).all()
    return [{"category": c, "count": n} for c, n in rows]


@router.get("/sitemap")
def sitemap(db: Session = Depends(get_db)):
    rows = db.scalars(_visible_stmt().order_by(Deal.updated_at.desc()).limit(5000)).all()
    return [{"slug": d.slug, "updated_at": iso(d.updated_at), "active": d.status in VISIBLE} for d in rows]
