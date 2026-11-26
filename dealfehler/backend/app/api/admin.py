"""Admin-/Dashboard-API (JWT, Rollen viewer < editor < admin)."""
from __future__ import annotations

import csv
import io
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.agents.base import run_agent
from app.agents.master import ALL_AGENTS, MasterAgent
from app.agents.pipeline import ingest_items
from app.agents.publishing import cancel_pending, mark_manual_published
from app.agents.registry import default_context
from app.api.deps import admin, current_user, editor, viewer
from app.api.serializers import deal_out, iso, pub_out
from app.config import get_settings
from app.db import get_db
from app.domain.settings_store import get_value, set_value
from app.domain.status import InvalidTransition, transition
from app.domain.timeutil import aware, now
from app.models import (
    AgentRun,
    AgentState,
    AuditLog,
    Click,
    Commission,
    CostEntry,
    Deal,
    ErrorLog,
    PlatformState,
    Product,
    Publication,
    Report,
    Role,
    User,
)
from app.models import (
    DealStatus as S,
)
from app.models import (
    PublicationStatus as PS,
)
from app.ops import audit
from app.security import create_token, hash_password, verify_password
from app.sources.feed import parse_feed, parse_price

router = APIRouter(prefix="/api")


def _or404(obj, msg: str = "Nicht gefunden"):
    if obj is None:
        raise HTTPException(404, msg)
    return obj


# ------------------------------------------------------------------ Auth & Benutzer
class LoginIn(BaseModel):
    email: str = Field(max_length=255)  # bewusst ohne Format-Validierung (z.B. interne Domains)
    password: str = Field(max_length=200)


@router.post("/auth/login")
def login(body: LoginIn, db: Session = Depends(get_db)):
    u = db.scalar(select(User).where(User.email == body.email.lower()))
    if not u or not u.is_active or not verify_password(body.password, u.password_hash):
        raise HTTPException(401, "E-Mail oder Passwort falsch")
    return {"access_token": create_token(u.email, u.role.value), "token_type": "bearer", "role": u.role.value}


@router.get("/auth/me")
def me(u: User = Depends(current_user)):
    return {"email": u.email, "role": u.role.value}


class UserIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=10)
    role: Role = Role.VIEWER


@router.get("/users")
def list_users(db: Session = Depends(get_db), _: User = Depends(admin)):
    return [{"id": u.id, "email": u.email, "role": u.role.value, "is_active": u.is_active}
            for u in db.scalars(select(User).order_by(User.id))]


@router.post("/users", status_code=201)
def create_user(body: UserIn, db: Session = Depends(get_db), u: User = Depends(admin)):
    if db.scalar(select(User).where(User.email == body.email.lower())):
        raise HTTPException(409, "Benutzer existiert bereits")
    db.add(User(email=body.email.lower(), password_hash=hash_password(body.password), role=body.role))
    audit(db, u.email, "user.create", email=body.email, role=body.role.value)
    db.commit()
    return {"ok": True}


class UserPatch(BaseModel):
    role: Role | None = None
    is_active: bool | None = None


@router.patch("/users/{uid}")
def patch_user(uid: int, body: UserPatch, db: Session = Depends(get_db), u: User = Depends(admin)):
    target = _or404(db.get(User, uid))
    if body.role is not None:
        target.role = body.role
    if body.is_active is not None:
        target.is_active = body.is_active
    audit(db, u.email, "user.update", id=uid, **body.model_dump(exclude_none=True, mode="json"))
    db.commit()
    return {"ok": True}


# ------------------------------------------------------------------ Übersicht
def _range(days: int) -> tuple[datetime, datetime]:
    t = now()
    return t - timedelta(days=days), t


@router.get("/dashboard/overview")
def overview(days: int = Query(1, ge=1, le=365), platform: str | None = None, db: Session = Depends(get_db),
             _: User = Depends(viewer)):
    start, end = _range(days)
    cnt = lambda m, *w: db.scalar(select(func.count()).select_from(m).where(*w)) or 0  # noqa: E731
    pub_where = [Publication.status == PS.PUBLISHED, Publication.published_at >= start]
    click_where = [Click.created_at >= start]
    if platform:
        pub_where.append(Publication.platform == platform)
        click_where.append(Click.channel == platform)
    comm = dict(db.execute(select(Commission.status, func.coalesce(func.sum(Commission.commission_cents), 0))
                           .where(Commission.occurred_at >= start).group_by(Commission.status)).all())
    published_by = {k.value: v for k, v in db.execute(
        select(Publication.platform, func.count()).where(*pub_where).group_by(Publication.platform)).all()}
    reach = {"instagram": 0, "pinterest": 0}
    for pf, metrics in db.execute(select(Publication.platform, Publication.metrics).where(*pub_where)).all():
        if pf.value == "instagram":
            reach["instagram"] += int((metrics or {}).get("reach") or 0)
        if pf.value == "pinterest":
            reach["pinterest"] += int((metrics or {}).get("IMPRESSION") or 0)
    # Zeitreihe (täglich)
    series = []
    for i in range(min(days, 90) - 1, -1, -1):
        d0 = (end - timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
        d1 = d0 + timedelta(days=1)
        series.append({
            "date": d0.date().isoformat(),
            "deals": cnt(Deal, Deal.created_at >= d0, Deal.created_at < d1),
            "published": cnt(Publication, Publication.status == PS.PUBLISHED, Publication.published_at >= d0,
                             Publication.published_at < d1),
            "clicks": cnt(Click, Click.created_at >= d0, Click.created_at < d1),
            "commission_cents": int(db.scalar(select(func.coalesce(func.sum(Commission.commission_cents), 0)).where(
                Commission.occurred_at >= d0, Commission.occurred_at < d1, Commission.status != "rejected")) or 0),
        })
    return {
        "range": {"from": iso(start), "to": iso(end), "days": days},
        "deals_found": cnt(Deal, Deal.created_at >= start),
        "price_error_suspects": cnt(Deal, Deal.created_at >= start, Deal.score >= 90),
        "published": sum(published_by.values()), "published_by_platform": published_by,
        "instagram_reach": reach["instagram"], "pinterest_impressions": reach["pinterest"],
        "whatsapp_pending": cnt(Publication, Publication.platform == "whatsapp",
                                Publication.status == PS.PENDING_APPROVAL),
        "whatsapp_published": cnt(Publication, Publication.platform == "whatsapp", *pub_where),
        "clicks": cnt(Click, *click_where),
        "commission_estimated_cents": int(comm.get("estimated", 0)),
        "commission_confirmed_cents": int(comm.get("confirmed", 0)),
        "cost_usd": round(float(db.scalar(select(func.coalesce(func.sum(CostEntry.cost_usd), 0)).where(
            CostEntry.created_at >= start)) or 0), 4),
        "errors": cnt(ErrorLog, ErrorLog.created_at >= start, ErrorLog.level == "error"),
        "pipeline": {s.value: cnt(Deal, Deal.status == s) for s in S},
        "dry_run": get_settings().dry_run,
        "global_kill_switch": bool(get_value(db, "global_kill_switch", False)),
        "series": series,
    }


# ------------------------------------------------------------------ Deals
@router.get("/deals")
def list_deals(status: str | None = None, deal_type: str | None = None, category: str | None = None,
               q: str | None = None, min_score: int = 0, limit: int = Query(50, le=200), offset: int = 0,
               sort: str = "created", db: Session = Depends(get_db), _: User = Depends(viewer)):
    stmt = select(Deal).join(Product).where(Deal.score >= min_score)
    if status:
        stmt = stmt.where(Deal.status == S(status))
    if deal_type:
        stmt = stmt.where(Deal.deal_type == deal_type)
    if category:
        stmt = stmt.where(Product.category == category)
    if q:
        stmt = stmt.where(or_(Product.title.ilike(f"%{q}%"), Product.external_id == q.upper()))
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    order = {"score": Deal.score.desc(), "priority": Deal.priority.desc()}.get(sort, Deal.created_at.desc())
    rows = db.scalars(stmt.order_by(order).limit(limit).offset(offset)).all()
    return {"total": total, "items": [deal_out(d) for d in rows]}


def _deal(db: Session, deal_id: int) -> Deal:
    d = db.get(Deal, deal_id)
    if not d:
        raise HTTPException(404, "Deal nicht gefunden")
    return d


@router.get("/deals/{deal_id}")
def get_deal(deal_id: int, db: Session = Depends(get_db), _: User = Depends(viewer)):
    return deal_out(_deal(db, deal_id), full=True)


class DealPatch(BaseModel):
    status: S | None = None
    editorial_note: str | None = None
    confirmed_price_error: bool | None = None
    note: str | None = None


@router.patch("/deals/{deal_id}")
def patch_deal(deal_id: int, body: DealPatch, db: Session = Depends(get_db), u: User = Depends(editor)):
    d = _deal(db, deal_id)
    if body.editorial_note is not None:
        d.editorial_note = body.editorial_note
    if body.confirmed_price_error is not None:
        if u.role != Role.ADMIN:
            raise HTTPException(403, "Nur Admins dürfen einen Preisfehler als bestätigt markieren")
        d.confirmed_price_error = body.confirmed_price_error
    if body.status is not None:
        try:
            transition(db, d, body.status, u.email, body.note)
        except InvalidTransition as e:
            raise HTTPException(409, str(e)) from None
        if body.status in (S.EXPIRED, S.REJECTED, S.FAILED):
            cancel_pending(db, d, f"Manuell: {body.status.value}", PS.CANCELLED)
    audit(db, u.email, "deal.update", id=deal_id, **body.model_dump(exclude_none=True, mode="json"))
    db.commit()
    return deal_out(d, full=True)


class ConfirmPriceIn(BaseModel):
    price: str  # "19,99"


@router.post("/deals/{deal_id}/confirm-price")
def confirm_price(deal_id: int, body: ConfirmPriceIn, db: Session = Depends(get_db), u: User = Depends(editor)):
    """Manuelle Preisbestätigung (z.B. für Feed-Deals ohne Live-Preisquelle)."""
    from app.agents.pipeline import apply_recheck
    from app.sources.base import SourceItem

    d = _deal(db, deal_id)
    cents = parse_price(body.price)
    if cents is None:
        raise HTTPException(422, "Preis ungültig")
    t = now()
    it = SourceItem(merchant=d.product.merchant, external_id=d.product.external_id, title=d.product.title,
                    product_url=d.product.product_url, category=d.product.category, price_cents=cents,
                    observed_at=t, source=f"manual:{u.email}")
    if d.status in (S.SCHEDULED, S.APPROVED, S.PUBLISHED) and cents == d.current_price_cents:
        d.price_checked_at = t
        for p in d.publications:
            if p.status == PS.PAUSED and p.last_error and "Preis veraltet" in p.last_error:
                p.status, p.last_error = PS.SCHEDULED, None
        outcome = "refreshed"
    elif d.status == S.IN_REVIEW:
        outcome = apply_recheck(db, d, it, t, u.email)
    else:
        raise HTTPException(409, f"Preisbestätigung im Status {d.status.value} nicht möglich")
    audit(db, u.email, "deal.confirm_price", id=deal_id, cents=cents, outcome=outcome)
    db.commit()
    return {"outcome": outcome, "deal": deal_out(d)}


@router.post("/products/import")
async def import_feed(file: UploadFile = File(...), merchant: str = "amazon_de", db: Session = Depends(get_db),
                      u: User = Depends(editor)):
    raw = (await file.read()).decode("utf-8-sig", errors="replace")
    items, errors = parse_feed(raw, source="feed", default_merchant=merchant)
    stats = ingest_items(db, items, actor=f"import:{u.email}")
    audit(db, u.email, "feed.import", filename=file.filename, **stats)
    db.commit()
    return {**stats, "errors": errors[:50]}


# ------------------------------------------------------------------ Veröffentlichungen
@router.get("/publications")
def list_publications(platform: str | None = None, status: str | None = None, limit: int = Query(100, le=500),
                      db: Session = Depends(get_db), _: User = Depends(viewer)):
    stmt = select(Publication)
    if platform:
        stmt = stmt.where(Publication.platform == platform)
    if status:
        stmt = stmt.where(Publication.status == PS(status))
    rows = db.scalars(stmt.order_by(Publication.scheduled_at.desc().nulls_last(), Publication.id.desc()).limit(limit))
    return [pub_out(p) for p in rows]


def _pub(db: Session, pid: int) -> Publication:
    p = db.get(Publication, pid)
    if not p:
        raise HTTPException(404, "Beitrag nicht gefunden")
    return p


class PubPatch(BaseModel):
    caption: str | None = None
    scheduled_at: datetime | None = None


@router.patch("/publications/{pid}")
def patch_pub(pid: int, body: PubPatch, db: Session = Depends(get_db), u: User = Depends(editor)):
    from app.agents.pipeline import run_compliance

    p = _pub(db, pid)
    if p.status not in (PS.DRAFT, PS.SCHEDULED, PS.PENDING_APPROVAL, PS.PAUSED):
        raise HTTPException(409, "Beitrag kann nicht mehr bearbeitet werden")
    if body.caption is not None:
        p.caption = body.caption
        res = run_compliance(db, p, now())
        if not res.passed:
            db.rollback()
            raise HTTPException(422, {"message": "Compliance-Prüfung fehlgeschlagen",
                                      "issues": [i.as_dict() for i in res.issues]})
    if body.scheduled_at is not None:
        p.scheduled_at = aware(body.scheduled_at)
    audit(db, u.email, "publication.update", id=pid)
    db.commit()
    return pub_out(p)


@router.post("/publications/{pid}/cancel")
def cancel_pub(pid: int, db: Session = Depends(get_db), u: User = Depends(editor)):
    p = _pub(db, pid)
    if p.status in (PS.PUBLISHED, PS.PUBLISHING):
        raise HTTPException(409, "Bereits veröffentlicht")
    p.status = PS.CANCELLED
    audit(db, u.email, "publication.cancel", id=pid)
    db.commit()
    return pub_out(p)


@router.post("/publications/{pid}/resume")
def resume_pub(pid: int, db: Session = Depends(get_db), u: User = Depends(editor)):
    p = _pub(db, pid)
    if p.status != PS.PAUSED:
        raise HTTPException(409, "Nur pausierte Beiträge können fortgesetzt werden")
    if p.price_cents_at_creation != p.deal.current_price_cents:
        raise HTTPException(409, "Preis hat sich geändert – Beitrag muss neu erstellt werden")
    p.status, p.last_error, p.scheduled_at = PS.SCHEDULED, None, max(aware(p.scheduled_at) or now(), now())
    audit(db, u.email, "publication.resume", id=pid)
    db.commit()
    return pub_out(p)


class ManualPublishedIn(BaseModel):
    external_url: str | None = None


@router.post("/publications/{pid}/mark-published")
def mark_published(pid: int, body: ManualPublishedIn, db: Session = Depends(get_db), u: User = Depends(editor)):
    """WhatsApp-Kanal / Newsletter: nach manueller Veröffentlichung bestätigen."""
    from app.agents.pipeline import run_compliance

    p = _pub(db, pid)
    res = run_compliance(db, p, now())
    if not res.passed:
        db.commit()
        raise HTTPException(422, {"message": "Compliance-Prüfung fehlgeschlagen – Preis neu prüfen",
                                  "issues": [i.as_dict() for i in res.issues]})
    try:
        mark_manual_published(db, p, now(), u.email, body.external_url)
    except ValueError as e:
        raise HTTPException(409, str(e)) from None
    audit(db, u.email, "publication.mark_published", id=pid)
    db.commit()
    return pub_out(p)


# ------------------------------------------------------------------ Plattformen / Not-Aus
def _platform_out(st: PlatformState, db: Session) -> dict:
    from app.domain.frequency import published_last_24h

    return {
        "platform": st.platform, "enabled": st.enabled, "kill_switch": st.kill_switch,
        "requires_manual_approval": st.requires_manual_approval, "daily_limit": st.daily_limit,
        "daily_limit_max": st.daily_limit_max, "ramp_step": st.ramp_step, "min_interval_minutes": st.min_interval_minutes,
        "quiet_hours_start": st.quiet_hours_start, "quiet_hours_end": st.quiet_hours_end, "min_score": st.min_score,
        "repost_cooldown_days": st.repost_cooldown_days, "consecutive_errors": st.consecutive_errors,
        "paused_until": iso(st.paused_until), "pause_reason": st.pause_reason,
        "published_24h": published_last_24h(db, st.platform, now()),
        "scheduled": db.scalar(select(func.count()).select_from(Publication).where(
            Publication.platform == st.platform, Publication.status == PS.SCHEDULED)) or 0,
    }


@router.get("/platforms")
def platforms(db: Session = Depends(get_db), _: User = Depends(viewer)):
    return [_platform_out(st, db) for st in db.scalars(select(PlatformState).order_by(PlatformState.platform))]


class PlatformPatch(BaseModel):
    enabled: bool | None = None
    daily_limit: int | None = Field(None, ge=0, le=500)
    daily_limit_max: int | None = Field(None, ge=0, le=500)
    ramp_step: int | None = Field(None, ge=0, le=10)
    min_interval_minutes: int | None = Field(None, ge=0, le=1440)
    quiet_hours_start: int | None = Field(None, ge=0, le=23)
    quiet_hours_end: int | None = Field(None, ge=0, le=23)
    min_score: int | None = Field(None, ge=50, le=100)
    repost_cooldown_days: int | None = Field(None, ge=0, le=365)
    requires_manual_approval: bool | None = None


@router.patch("/platforms/{name}")
def patch_platform(name: str, body: PlatformPatch, db: Session = Depends(get_db), u: User = Depends(admin)):
    st = db.get(PlatformState, name)
    if not st:
        raise HTTPException(404, "Plattform unbekannt")
    data = body.model_dump(exclude_none=True)
    if data.get("enabled") and name not in ("website", "whatsapp", "newsletter") and not get_settings().dry_run:
        from app.publishers.messaging import get_publisher

        if not get_publisher(name).is_configured():
            raise HTTPException(409, f"{name}: Zugangsdaten fehlen (siehe API-Verbindungen)")
    for k, v in data.items():
        setattr(st, k, v)
    if st.daily_limit > st.daily_limit_max:
        st.daily_limit = st.daily_limit_max
    audit(db, u.email, "platform.update", platform=name, **data)
    db.commit()
    return _platform_out(st, db)


@router.post("/platforms/{name}/kill")
def kill_platform(name: str, db: Session = Depends(get_db), u: User = Depends(editor)):
    st = _or404(db.get(PlatformState, name), "Plattform unbekannt")
    st.kill_switch = True
    audit(db, u.email, "platform.kill", platform=name)
    db.commit()
    return _platform_out(st, db)


@router.post("/platforms/{name}/resume")
def resume_platform(name: str, db: Session = Depends(get_db), u: User = Depends(admin)):
    st = _or404(db.get(PlatformState, name), "Plattform unbekannt")
    st.kill_switch, st.paused_until, st.pause_reason, st.consecutive_errors = False, None, None, 0
    audit(db, u.email, "platform.resume", platform=name)
    db.commit()
    return _platform_out(st, db)


class KillAllIn(BaseModel):
    active: bool


@router.post("/system/kill-switch")
def global_kill(body: KillAllIn, db: Session = Depends(get_db), u: User = Depends(editor)):
    if not body.active and u.role != Role.ADMIN:
        raise HTTPException(403, "Nur Admins dürfen den Not-Aus aufheben")
    set_value(db, "global_kill_switch", body.active)
    audit(db, u.email, "system.kill_switch", active=body.active)
    db.commit()
    return {"global_kill_switch": body.active}


# ------------------------------------------------------------------ Agenten
@router.get("/agents")
def agents(db: Session = Depends(get_db), _: User = Depends(viewer)):
    out = []
    for name, cls in {"master": MasterAgent, **ALL_AGENTS}.items():
        st = db.get(AgentState, name)
        out.append({"name": name, "title": cls.title, "description": cls.description,
                    "enabled": st.enabled if st else True, "last_run_at": iso(st.last_run_at) if st else None,
                    "last_status": st.last_status if st else None, "last_error": st.last_error if st else None,
                    "consecutive_failures": st.consecutive_failures if st else 0,
                    "run_count": st.run_count if st else 0})
    return out


@router.get("/agents/{name}/runs")
def agent_runs(name: str, limit: int = 20, db: Session = Depends(get_db), _: User = Depends(viewer)):
    rows = db.scalars(select(AgentRun).where(AgentRun.agent == name).order_by(AgentRun.id.desc()).limit(limit))
    return [{"id": r.id, "status": r.status, "stats": r.stats, "error": r.error, "started_at": iso(r.started_at),
             "finished_at": iso(r.finished_at)} for r in rows]


class AgentPatch(BaseModel):
    enabled: bool


@router.patch("/agents/{name}")
def patch_agent(name: str, body: AgentPatch, db: Session = Depends(get_db), u: User = Depends(admin)):
    if name not in ALL_AGENTS and name != "master":
        raise HTTPException(404, "Agent unbekannt")
    st = db.get(AgentState, name) or AgentState(name=name)
    st.enabled = body.enabled
    if body.enabled:
        st.consecutive_failures = 0
    db.add(st)
    audit(db, u.email, "agent.update", agent=name, enabled=body.enabled)
    db.commit()
    return {"name": name, "enabled": st.enabled}


@router.post("/agents/{name}/run")
def trigger_agent(name: str, db: Session = Depends(get_db), u: User = Depends(editor)):
    cls = MasterAgent if name == "master" else ALL_AGENTS.get(name)
    if not cls:
        raise HTTPException(404, "Agent unbekannt")
    run = run_agent(db, cls(), default_context())
    audit(db, u.email, "agent.run", agent=name, status=run.status)
    db.commit()
    return {"status": run.status, "stats": run.stats, "error": run.error}


# ------------------------------------------------------------------ Statistiken & Umsatz
@router.get("/stats/clicks")
def click_stats(days: int = 30, db: Session = Depends(get_db), _: User = Depends(viewer)):
    start, _e = _range(days)
    by_channel = dict(db.execute(select(Click.channel, func.count()).where(Click.created_at >= start)
                                 .group_by(Click.channel)).all())
    by_category = dict(db.execute(select(Product.category, func.count()).select_from(Click)
                                  .join(Deal, Deal.id == Click.deal_id)
                                  .join(Product, Product.id == Deal.product_id).where(Click.created_at >= start)
                                  .group_by(Product.category)).all())
    top = db.execute(select(Deal.id, Product.title, func.count().label("n")).select_from(Deal)
                     .join(Click, Click.deal_id == Deal.id)
                     .join(Product, Product.id == Deal.product_id).where(Click.created_at >= start)
                     .group_by(Deal.id, Product.title).order_by(func.count().desc()).limit(10)).all()
    return {"by_channel": by_channel, "by_category": by_category,
            "top_deals": [{"deal_id": i, "title": t, "clicks": n} for i, t, n in top]}


@router.get("/stats/revenue")
def revenue(days: int = 30, db: Session = Depends(get_db), _: User = Depends(viewer)):
    start, _e = _range(days)
    rows = db.execute(select(Commission.network, Commission.status, func.sum(Commission.commission_cents),
                             func.sum(Commission.revenue_cents), func.count())
                      .where(Commission.occurred_at >= start).group_by(Commission.network, Commission.status)).all()
    pubs = db.scalar(select(func.count()).select_from(Publication).where(
        Publication.status == PS.PUBLISHED, Publication.published_at >= start)) or 0
    cost = float(db.scalar(select(func.coalesce(func.sum(CostEntry.cost_usd), 0)).where(
        CostEntry.created_at >= start)) or 0)
    confirmed = sum(int(r[2] or 0) for r in rows if r[1] == "confirmed")
    return {
        "rows": [{"network": n, "status": s, "commission_cents": int(c or 0), "revenue_cents": int(rv or 0),
                  "orders": k} for n, s, c, rv, k in rows],
        "publications": pubs, "cost_usd": round(cost, 4),
        "cost_per_publication_usd": round(cost / pubs, 4) if pubs else None,
        "confirmed_commission_per_publication_cents": round(confirmed / pubs, 1) if pubs else None,
    }


COMMISSION_ALIASES = {
    "ref": ["ref", "id", "order_id", "bestellnummer", "transaction_id"],
    "asin": ["asin", "product_id", "artikel"],
    "tracking_id": ["tracking_id", "tracking-id", "tag"],
    "date": ["date", "datum", "occurred_at", "versanddatum"],
    "revenue": ["revenue", "umsatz", "preis", "price", "sale_amount"],
    "commission": ["commission", "provision", "einnahmen", "earnings"],
    "status": ["status"],
}


@router.post("/commissions/import")
async def import_commissions(file: UploadFile = File(...), network: str = "amazon", db: Session = Depends(get_db),
                             u: User = Depends(editor)):
    """CSV-Import aus Partnerprogramm-Berichten (z.B. PartnerNet "Einnahmenbericht").
    Status: 'confirmed' wenn Spalte status=confirmed/bestätigt, sonst 'estimated'."""
    text = (await file.read()).decode("utf-8-sig", errors="replace")
    dialect = csv.Sniffer().sniff(text[:2048], delimiters=",;\t") if text.strip() else csv.excel
    reader = csv.DictReader(io.StringIO(text), dialect=dialect)
    header = {h.lower().strip(): h for h in (reader.fieldnames or [])}

    def col(row, key):
        for a in COMMISSION_ALIASES[key]:
            if a in header:
                return row.get(header[a])
        return None

    added, errors = 0, []
    for n, row in enumerate(reader, start=2):
        try:
            asin = (col(row, "asin") or "").strip().upper() or None
            date = datetime.fromisoformat((col(row, "date") or "").strip()[:10])
            ref = (col(row, "ref") or f"{asin}-{date.date()}-{n}").strip()
            if db.scalar(select(Commission.id).where(Commission.network == network, Commission.external_ref == ref)):
                continue
            deal_id = None
            if asin:
                deal_id = db.scalar(select(Deal.id).join(Product).where(Product.external_id == asin)
                                    .order_by(Deal.created_at.desc()).limit(1))
            st = (col(row, "status") or "").lower()
            db.add(Commission(network=network, external_ref=ref, tracking_id=col(row, "tracking_id"),
                              product_external_id=asin, deal_id=deal_id,
                              revenue_cents=parse_price(col(row, "revenue")) or 0,
                              commission_cents=parse_price(col(row, "commission")) or 0,
                              status="confirmed" if st in ("confirmed", "bestätigt", "approved") else
                              ("rejected" if st in ("rejected", "storniert") else "estimated"),
                              occurred_at=aware(date)))
            added += 1
        except (ValueError, TypeError) as e:
            errors.append(f"Zeile {n}: {e}")
    audit(db, u.email, "commissions.import", added=added)
    db.commit()
    return {"added": added, "errors": errors[:50]}


# ------------------------------------------------------------------ Betrieb
@router.get("/errors")
def errors(limit: int = 100, source: str | None = None, include_resolved: bool = False,
           db: Session = Depends(get_db), _: User = Depends(viewer)):
    stmt = select(ErrorLog)
    if source:
        stmt = stmt.where(ErrorLog.source.like(f"{source}%"))
    if not include_resolved:
        stmt = stmt.where(ErrorLog.resolved.is_(False))
    return [{"id": e.id, "source": e.source, "level": e.level, "message": e.message, "context": e.context,
             "resolved": e.resolved, "created_at": iso(e.created_at)}
            for e in db.scalars(stmt.order_by(ErrorLog.id.desc()).limit(limit))]


@router.post("/errors/{eid}/resolve")
def resolve_error(eid: int, db: Session = Depends(get_db), u: User = Depends(editor)):
    e = db.get(ErrorLog, eid)
    if not e:
        raise HTTPException(404, "Nicht gefunden")
    e.resolved = True
    db.commit()
    return {"ok": True}


@router.get("/costs")
def costs(days: int = 30, db: Session = Depends(get_db), _: User = Depends(viewer)):
    from app.llm.client import spent_usd

    s = get_settings()
    start, _e = _range(days)
    rows = db.execute(select(CostEntry.provider, CostEntry.operation, func.count(), func.sum(CostEntry.cost_usd))
                      .where(CostEntry.created_at >= start).group_by(CostEntry.provider, CostEntry.operation)).all()
    return {
        "rows": [{"provider": p, "operation": o, "calls": c, "cost_usd": round(float(v or 0), 4)} for p, o, c, v in rows],
        "llm_today_usd": round(spent_usd(db, "anthropic", 1), 4), "llm_daily_budget_usd": s.llm_daily_budget_usd,
        "llm_month_usd": round(spent_usd(db, "anthropic", 30), 4), "llm_monthly_budget_usd": s.llm_monthly_budget_usd,
    }


@router.get("/connections")
def connections(check: bool = False, db: Session = Depends(get_db), _: User = Depends(viewer)):
    """Status der Zugänge. Werte von Geheimnissen werden nie zurückgegeben."""
    from app.publishers.messaging import get_publisher

    s = get_settings()
    items = [
        {"key": "amazon", "name": "Amazon PartnerNet", "configured": bool(s.amazon_partner_tag),
         "detail": f"Partner-Tag: {s.amazon_partner_tag}" if s.amazon_partner_tag else "AMAZON_PARTNER_TAG fehlt"},
        {"key": "keepa", "name": "Keepa API (Preishistorie)", "configured": bool(s.keepa_api_key)},
        {"key": "anthropic", "name": "Claude API (Texte)", "configured": bool(s.anthropic_api_key),
         "detail": f"Modell {s.llm_model}, Tagesbudget {s.llm_daily_budget_usd} $"},
        {"key": "s3", "name": "S3-Medienspeicher", "configured": s.storage_backend == "s3" and bool(s.s3_bucket),
         "detail": "Instagram benötigt öffentlich erreichbare https-Medien"},
        {"key": "awin", "name": "Awin", "configured": bool(s.awin_api_token and s.awin_publisher_id)},
        {"key": "alerts", "name": "Alarme (Telegram/Webhook)",
         "configured": bool((s.telegram_bot_token and s.alert_telegram_chat_id) or s.alert_webhook_url)},
    ]
    for pf, name in [("instagram", "Instagram (Meta Graph API)"), ("pinterest", "Pinterest API v5"),
                     ("telegram", "Telegram-Kanal (Bot API)"), ("whatsapp", "WhatsApp-Kanal (manuell)")]:
        pub = get_publisher(pf)
        entry = {"key": pf, "name": name, "configured": pub.is_configured() if pf != "whatsapp" else
                 bool(s.whatsapp_channel_invite_url)}
        if check:
            entry["health"] = pub.health()
        items.append(entry)
    return {"dry_run": s.dry_run, "items": items}


@router.get("/reports")
def reports(kind: str | None = None, limit: int = 30, db: Session = Depends(get_db), _: User = Depends(viewer)):
    stmt = select(Report)
    if kind:
        stmt = stmt.where(Report.kind == kind)
    return [{"id": r.id, "kind": r.kind, "period": r.period, "content": r.content, "created_at": iso(r.created_at)}
            for r in db.scalars(stmt.order_by(Report.id.desc()).limit(limit))]


@router.get("/audit")
def audit_log(limit: int = 100, db: Session = Depends(get_db), _: User = Depends(admin)):
    return [{"actor": a.actor, "action": a.action, "details": a.details, "at": iso(a.created_at)}
            for a in db.scalars(select(AuditLog).order_by(AuditLog.id.desc()).limit(limit))]


class SettingsIn(BaseModel):
    demo_mode: bool | None = None


@router.get("/settings")
def get_settings_api(db: Session = Depends(get_db), _: User = Depends(viewer)):
    s = get_settings()
    return {"demo_mode": bool(get_value(db, "demo_mode", False)), "dry_run": s.dry_run, "timezone": s.timezone,
            "max_price_age_minutes": s.max_price_age_minutes, "public_base_url": s.public_base_url,
            "learning": {k: get_value(db, f"learning.{k}", None) for k in
                         ("category_weights", "template_weights", "best_hours")}}


@router.patch("/settings")
def patch_settings(body: SettingsIn, db: Session = Depends(get_db), u: User = Depends(admin)):
    if body.demo_mode is not None:
        set_value(db, "demo_mode", body.demo_mode)
    audit(db, u.email, "settings.update", **body.model_dump(exclude_none=True))
    db.commit()
    return {"ok": True}
