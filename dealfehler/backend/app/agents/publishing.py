"""Master-Priorisierung, Scheduler, Plattform-Veröffentlichung und Preisüberwachung."""
from __future__ import annotations

import math
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.base import Agent, AgentContext
from app.agents.pipeline import apply_recheck, run_compliance
from app.config import get_settings
from app.domain import frequency as freq
from app.domain.dedup import recently_posted_product
from app.domain.settings_store import get_value
from app.domain.status import transition
from app.domain.timeutil import aware
from app.models import Deal, PlatformState, Publication
from app.models import DealStatus as S
from app.models import PublicationStatus as PS
from app.ops import log_error, send_alert
from app.publishers.base import PublishRequest
from app.storage import get_storage

# Geschätzte Amazon-Provisionssätze je Kategorie (nur zur Priorisierung, nicht für Umsatzangaben).
# Bitte mit der aktuellen PartnerNet-Gebührentabelle abgleichen.
COMMISSION_HINT = {"technik": 0.03, "gaming": 0.03, "haushalt": 0.07, "kueche": 0.07, "werkzeug": 0.07,
                   "garten": 0.07, "baby": 0.07, "auto": 0.07, "sport": 0.07, "drogerie": 0.07, "sonstiges": 0.05}


def priority(db: Session, d: Deal, t) -> float:
    """Erwarteter Wert: Score × Kategorie-Lernfaktor × Provision × Preis-Nutzen × Frische."""
    cat_w = (get_value(db, "learning.category_weights", {}) or {}).get(d.product.category, 1.0)
    commission = d.current_price_cents / 100 * COMMISSION_HINT.get(d.product.category, 0.05)
    money = math.log1p(max(commission, 0.1))
    age_h = (t - aware(d.created_at)).total_seconds() / 3600
    fresh = 0.5 ** (age_h / 24)
    demand = 1.1 if (d.product.review_count or 0) > 500 else 1.0
    return round(d.score * cat_w * (0.5 + money) * (0.4 + 0.6 * fresh) * demand, 3)


class MasterPriorityAgent(Agent):
    name, title = "prioritizer", "Master-Priorisierung"
    description = "Priorisiert freigegebene Deals nach erwartetem Umsatz."

    def run(self, db: Session, ctx: AgentContext) -> dict:
        t = ctx.clock()
        deals = db.scalars(select(Deal).where(Deal.status.in_([S.APPROVED, S.SCHEDULED]))).all()
        for d in deals:
            d.priority = priority(db, d, t)
        return {"prioritized": len(deals)}


class SchedulerAgent(Agent):
    name, title = "scheduler", "Scheduler"
    description = "Plant freigegebene Entwürfe in freie Zeitfenster je Plattform (Limits, Abstände, Ruhezeiten)."

    def run(self, db: Session, ctx: AgentContext) -> dict:
        t = ctx.clock()
        stats = {"scheduled": 0, "manual": 0, "skipped_duplicate": 0, "skipped_score": 0, "capacity_full": 0}
        deals = db.scalars(select(Deal).where(Deal.status == S.APPROVED).order_by(Deal.priority.desc())).all()
        horizon = t + timedelta(hours=24)
        for d in deals:
            any_planned = False
            for p in [p for p in d.publications if p.status == PS.DRAFT]:
                pf = p.platform.value
                st = db.get(PlatformState, pf)
                if st is None or not st.enabled or st.kill_switch:
                    continue
                if d.score < st.min_score:
                    stats["skipped_score"] += 1
                    p.status, p.last_error = PS.CANCELLED, f"Score {d.score} < Plattform-Minimum {st.min_score}"
                    continue
                if pf != "website" and recently_posted_product(db, pf, d.product_id, d.current_price_cents,
                                                                st.repost_cooldown_days, t):
                    stats["skipped_duplicate"] += 1
                    p.status, p.last_error = PS.CANCELLED, "Duplikat im Cooldown-Zeitraum"
                    continue
                if st.requires_manual_approval:
                    p.status, p.scheduled_at = PS.PENDING_APPROVAL, t
                    stats["manual"] += 1
                    any_planned = True
                    continue
                taken = [aware(x) for x in db.scalars(select(Publication.scheduled_at).where(
                    Publication.platform == pf, Publication.status == PS.SCHEDULED)).all() if x]
                planned_24h = len([x for x in taken if x <= horizon]) + freq.published_last_24h(db, pf, t)
                if planned_24h >= st.daily_limit:
                    stats["capacity_full"] += 1
                    continue  # bleibt Entwurf, nächster Lauf versucht es erneut
                p.scheduled_at = freq.next_slot(db, pf, t, taken)
                p.status = PS.SCHEDULED
                stats["scheduled"] += 1
                any_planned = True
            if any_planned:
                transition(db, d, S.SCHEDULED, self.name)
        return stats


def cancel_pending(db: Session, d: Deal, reason: str, status: PS = PS.PAUSED) -> int:
    n = 0
    for p in d.publications:
        if p.status in (PS.SCHEDULED, PS.PENDING_APPROVAL, PS.DRAFT):
            p.status, p.last_error = status, reason
            n += 1
    return n


class PublisherAgent(Agent):
    name, title = "publisher", "Plattform-Veröffentlichung"
    description = "Veröffentlicht fällige Beiträge über offizielle APIs – mit Nachprüfung, Drosselung und Not-Aus."

    def run(self, db: Session, ctx: AgentContext) -> dict:
        s = get_settings()
        t = ctx.clock()
        stats = {"published": 0, "dry_run": 0, "rescheduled": 0, "paused": 0, "failed": 0, "manual": 0}
        q = (select(Publication).where(Publication.status == PS.SCHEDULED, Publication.scheduled_at <= t)
             .order_by(Publication.scheduled_at).limit(20))
        if db.bind.dialect.name == "postgresql":
            q = q.with_for_update(skip_locked=True)
        for p in db.scalars(q).all():
            pf = p.platform.value
            dec = freq.can_publish(db, pf, t)
            if not dec.allowed:
                if dec.next_possible_at:
                    p.scheduled_at = dec.next_possible_at
                    stats["rescheduled"] += 1
                elif "Tageslimit" in dec.reason or "Ruhezeit" in dec.reason:
                    p.scheduled_at = freq.next_slot(db, pf, t + timedelta(minutes=30))
                    stats["rescheduled"] += 1
                # Not-Aus/deaktiviert: Beitrag bleibt liegen, nichts wird veröffentlicht
                continue
            d = p.deal
            # 1) Preis unmittelbar vor Veröffentlichung erneut prüfen
            checked = aware(d.price_checked_at)
            if checked is None or t - checked > timedelta(minutes=s.max_price_age_minutes):
                src = ctx.source_for(d.product.source)
                if src is None or not src.is_configured():
                    p.status, p.last_error = PS.PAUSED, "Preis veraltet – manuelle Bestätigung nötig"
                    stats["paused"] += 1
                    continue
                it = src.fetch_current([d.product.external_id]).get(d.product.external_id)
                if it is None or not it.available or abs(it.price_cents - d.current_price_cents) > d.current_price_cents * 0.02:
                    outcome = apply_recheck(db, d, it, t, self.name) if d.status in (S.SCHEDULED, S.PUBLISHED, S.APPROVED) else "changed"
                    cancel_pending(db, d, f"Preisprüfung vor Veröffentlichung: {outcome}")
                    stats["paused"] += 1
                    continue
                d.price_checked_at = t
            if p.price_cents_at_creation != d.current_price_cents:
                p.status, p.last_error = PS.PAUSED, "Preis seit Erstellung geändert"
                stats["paused"] += 1
                continue
            # 2) Compliance erneut (zeitabhängige Regeln)
            res = run_compliance(db, p, t)
            if not res.passed:
                p.status = PS.FAILED
                p.last_error = "; ".join(i.message for i in res.issues if i.severity == "error")
                stats["failed"] += 1
                continue
            # 3) Veröffentlichen
            p.status, p.attempts = PS.PUBLISHING, p.attempts + 1
            db.flush()
            if s.dry_run and pf != "website":
                p.status, p.published_at, p.external_id = PS.PUBLISHED, t, f"dry-run-{p.id}"
                p.metrics = {**(p.metrics or {}), "dry_run": True}
                stats["dry_run"] += 1
                self._mark_deal(db, d)
                continue
            pub = ctx.publisher(pf)
            if not pub.is_configured():
                p.status, p.last_error = PS.PAUSED, f"{pf} nicht konfiguriert"
                stats["paused"] += 1
                continue
            media_bytes = None
            if p.media and not p.media.public_url.startswith("https://"):
                try:
                    media_bytes = get_storage().get(p.media.storage_key)
                except OSError:
                    media_bytes = None
            req = PublishRequest(caption=p.caption, format=p.format, media_url=p.media.public_url if p.media else None,
                                 media_bytes=media_bytes, media_content_type="image/png", link_url=p.link_url,
                                 title=p.title, board=p.board)
            try:
                r = pub.publish(req)
            except Exception as e:  # Netzwerkfehler etc.
                from app.publishers.base import PublishResult

                r = PublishResult(False, error=f"{type(e).__name__}: {e}", retryable=True)
            if r.ok:
                p.status, p.published_at, p.external_id, p.external_url = PS.PUBLISHED, t, r.external_id, r.external_url
                p.last_error = None
                freq.register_success(db, pf)
                stats["published"] += 1
                self._mark_deal(db, d)
            elif r.manual:
                p.status = PS.PENDING_APPROVAL
                stats["manual"] += 1
            else:
                st = freq.register_error(db, pf, r.error or "unbekannt", t, rate_limited=r.rate_limited,
                                         retry_after_s=r.retry_after_s)
                p.last_error = r.error
                if r.retryable and p.attempts < 3:
                    p.status = PS.SCHEDULED
                    p.scheduled_at = t + timedelta(minutes=15 * p.attempts)
                    stats["rescheduled"] += 1
                else:
                    p.status = PS.FAILED
                    stats["failed"] += 1
                log_error(db, f"publisher:{pf}", r.error or "Veröffentlichung fehlgeschlagen",
                          context={"publication_id": p.id}, alert=bool(st.paused_until))
        return stats

    @staticmethod
    def _mark_deal(db: Session, d: Deal) -> None:
        if d.status != S.PUBLISHED:
            transition(db, d, S.PUBLISHED, "publisher")


def mark_manual_published(db: Session, p: Publication, t, actor: str, external_url: str | None = None) -> None:
    """WhatsApp/Newsletter: nach manueller Veröffentlichung durch einen Menschen."""
    if p.status != PS.PENDING_APPROVAL:
        raise ValueError("Beitrag wartet nicht auf manuelle Veröffentlichung")
    p.status, p.published_at, p.external_url = PS.PUBLISHED, t, external_url
    if p.deal.status != S.PUBLISHED:
        transition(db, p.deal, S.PUBLISHED, actor, f"manuell auf {p.platform.value} veröffentlicht", force=True)


class PriceWatchAgent(Agent):
    name, title = "price_watch", "Preisüberwachung"
    description = "Prüft geplante und veröffentlichte Deals; pausiert/korrigiert Beiträge bei Preisänderung oder Ende."

    def run(self, db: Session, ctx: AgentContext) -> dict:
        t = ctx.clock()
        stats = {"checked": 0, "changed": 0, "expired": 0, "paused_publications": 0}
        deals = db.scalars(select(Deal).where(Deal.status.in_([S.APPROVED, S.SCHEDULED, S.PUBLISHED]))).all()
        groups: dict[str, list[Deal]] = {}
        for d in deals:
            if d.valid_until and aware(d.valid_until) < t:
                transition(db, d, S.EXPIRED, self.name, "Gültigkeit abgelaufen")
                stats["paused_publications"] += cancel_pending(db, d, "Angebot abgelaufen", PS.CANCELLED)
                stats["expired"] += 1
                continue
            if d.price_checked_at and t - aware(d.price_checked_at) < timedelta(minutes=30):
                continue
            groups.setdefault(d.product.source, []).append(d)
        for src_name, items in groups.items():
            src = ctx.source_for(src_name)
            if src is None or not src.is_configured():
                continue
            cur = src.fetch_current([d.product.external_id for d in items])
            for d in items:
                stats["checked"] += 1
                it = cur.get(d.product.external_id)
                if it is None or not it.available:
                    transition(db, d, S.EXPIRED, self.name, "Nicht mehr verfügbar")
                    stats["paused_publications"] += cancel_pending(db, d, "Angebot beendet", PS.CANCELLED)
                    stats["expired"] += 1
                elif abs(it.price_cents - d.current_price_cents) > d.current_price_cents * 0.02:
                    old = d.current_price_cents
                    d.current_price_cents, d.verification_count, d.price_checked_at = it.price_cents, 0, t
                    transition(db, d, S.PRICE_CHANGED, self.name, f"{old/100:.2f} € → {it.price_cents/100:.2f} €")
                    stats["paused_publications"] += cancel_pending(db, d, "Preis geändert – neue Prüfung")
                    stats["changed"] += 1
                else:
                    d.price_checked_at = t
        if stats["changed"] or stats["expired"]:
            send_alert(f"Preisüberwachung: {stats['changed']} Preisänderungen, {stats['expired']} beendete Angebote")
        return stats
