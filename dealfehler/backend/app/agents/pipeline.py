"""Agenten der Deal-Pipeline: Deal Hunter → Preisprüfer → Affiliate → Creative → Compliance."""
from __future__ import annotations

import random
import re
import unicodedata
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.base import Agent, AgentContext
from app.config import get_settings
from app.creative import captions as cap
from app.creative.render import TEMPLATES, CreativeData, render_png
from app.domain import compliance as comp
from app.domain.affiliate import AffiliateError, amazon_link, validate_amazon_link
from app.domain.dedup import content_hash, deal_fingerprint
from app.domain.scoring import PriceObs, score_price
from app.domain.settings_store import get_value
from app.domain.status import transition
from app.domain.timeutil import aware, fmt_local
from app.llm.client import polish_hook
from app.models import (
    AffiliateLink,
    ComplianceCheck,
    Deal,
    DealType,
    MediaAsset,
    PlatformState,
    PricePoint,
    Product,
    Publication,
)
from app.models import (
    DealStatus as S,
)
from app.models import (
    PublicationStatus as PS,
)
from app.ops import log_error, send_alert
from app.sources.base import SourceItem
from app.storage import get_storage

ACTIVE = [S.NEW, S.IN_REVIEW, S.VERIFIED, S.MEDIA, S.APPROVED, S.SCHEDULED, S.PUBLISHED, S.PRICE_CHANGED]
LABELS = {"preisfehler_verdacht": "Preisfehler-Verdacht", "top_deal": "Top-Deal"}
PRICE_TOLERANCE = 0.02  # ±2 % gilt bei der Nachprüfung als "gleicher Preis"
MIN_RECHECK_GAP = timedelta(minutes=10)


def slugify(text: str, suffix: str) -> str:
    t = unicodedata.normalize("NFKD", text.replace("ß", "ss")).encode("ascii", "ignore").decode().lower()
    t = re.sub(r"[^a-z0-9]+", "-", t).strip("-")[:80].rstrip("-")
    return f"{t}-{suffix.lower()}"


def deal_label(deal: Deal) -> str:
    if deal.confirmed_price_error:
        return "Preisfehler"
    return LABELS.get(deal.deal_type.value, {"gutschein": "Gutschein-Deal", "tagesangebot": "Tagesangebot",
                                             "blitzangebot": "Blitzangebot"}.get(deal.deal_type.value, "Deal"))


# ---------------------------------------------------------------- Deal Hunter
def ingest_items(db: Session, items: list[SourceItem], actor: str = "deal_hunter") -> dict:
    created = updated = points = 0
    for it in items:
        prod = db.scalar(select(Product).where(Product.merchant == it.merchant, Product.external_id == it.external_id))
        if prod is None:
            prod = Product(merchant=it.merchant, external_id=it.external_id, title=it.title[:500], brand=it.brand,
                           category=it.category, product_url=it.product_url, source=it.source)
            db.add(prod)
            db.flush()
        else:
            prod.title, prod.category = it.title[:500], it.category
            if prod.source == "demo" or it.source != "demo":
                prod.source = it.source
        prod.rating, prod.review_count, prod.sales_rank = it.rating, it.review_count, it.sales_rank
        known = {aware(t) for t in db.scalars(select(PricePoint.observed_at).where(PricePoint.product_id == prod.id))}
        for h in it.history:
            if aware(h.observed_at) not in known:
                db.add(PricePoint(product_id=prod.id, price_cents=h.price_cents, source=it.source,
                                  available=h.available, observed_at=h.observed_at))
                points += 1
        if aware(it.observed_at) not in known:
            db.add(PricePoint(product_id=prod.id, price_cents=it.price_cents, list_price_cents=it.list_price_cents,
                              source=it.source, available=it.available, observed_at=it.observed_at))
            points += 1
        if not it.available:
            continue
        fp = deal_fingerprint(it.merchant, it.external_id, it.price_cents)
        active = db.scalar(select(Deal).where(Deal.product_id == prod.id, Deal.status.in_(ACTIVE))
                           .order_by(Deal.created_at.desc()))
        if active and active.fingerprint == fp:
            continue
        # Gleicher Preis wurde kürzlich schon bewertet (abgelehnt/abgelaufen) → nicht erneut anlegen
        if not active and db.scalar(select(Deal.id).where(
                Deal.product_id == prod.id, Deal.fingerprint == fp,
                Deal.created_at >= it.observed_at - timedelta(days=7)).limit(1)):
            continue
        if active:
            # Neuer Preis für einen laufenden Deal → zurück in die Prüfung
            active.current_price_cents = it.price_cents
            active.fingerprint = fp
            active.score_breakdown = {**(active.score_breakdown or {}), "other_sources": it.other_source_prices}
            if active.status not in (S.NEW, S.IN_REVIEW, S.PRICE_CHANGED):
                transition(db, active, S.PRICE_CHANGED, actor, "Preis hat sich bei neuer Erfassung geändert")
            active.verification_count = 0
            updated += 1
            continue
        dtype = {"gutschein": DealType.COUPON, "tagesangebot": DealType.DAILY_DEAL,
                 "blitzangebot": DealType.LIGHTNING}.get(it.deal_hint or "", DealType.DEAL)
        slug = slugify(it.title, f"{it.external_id}-{it.price_cents}")
        n = 2
        while db.scalar(select(Deal.id).where(Deal.slug == slug)):
            slug = slugify(it.title, f"{it.external_id}-{it.price_cents}-{n}")
            n += 1
        d = Deal(product_id=prod.id, slug=slug,
                 current_price_cents=it.price_cents, deal_type=dtype, fingerprint=fp, coupon_code=it.coupon_code,
                 valid_until=it.valid_until, score_breakdown={"other_sources": it.other_source_prices})
        db.add(d)
        db.flush()
        transition(db, d, S.NEW, actor, f"Gefunden über {it.source}", force=True)
        created += 1
    return {"items": len(items), "deals_created": created, "deals_updated": updated, "price_points": points}


class DealHunterAgent(Agent):
    name, title = "deal_hunter", "Amazon Deal Hunter"
    description = "Sucht über zugelassene Quellen (Keepa, Feeds) nach Angeboten und speichert Preisverläufe."

    def run(self, db: Session, ctx: AgentContext) -> dict:
        total: dict = {"sources": {}}
        demo = get_value(db, "demo_mode", False)
        for name, src in ctx.sources.items():
            if name == "demo" and not demo:
                continue
            if not src.is_configured():
                total["sources"][name] = "nicht konfiguriert"
                continue
            try:
                items = src.fetch_candidates()
            except Exception as e:
                log_error(db, f"source:{name}", f"Abruf fehlgeschlagen: {e}", exc=e)
                total["sources"][name] = "fehler"
                continue
            total["sources"][name] = ingest_items(db, items)
        return total


# ---------------------------------------------------------------- Preisfehler Hunter / Preisprüfer
def history_for(db: Session, product_id: int) -> list[PriceObs]:
    rows = db.execute(select(PricePoint.price_cents, PricePoint.observed_at, PricePoint.available)
                      .where(PricePoint.product_id == product_id)).all()
    return [PriceObs(p, aware(t), a) for p, t, a in rows]


def rescore(db: Session, deal: Deal, t) -> None:
    prod = deal.product
    lp = db.scalar(select(PricePoint.list_price_cents).where(PricePoint.product_id == prod.id,
                   PricePoint.list_price_cents.is_not(None)).order_by(PricePoint.observed_at.desc()).limit(1))
    res = score_price(deal.current_price_cents, history_for(db, prod.id), t, list_price_cents=lp,
                      other_source_prices=(deal.score_breakdown or {}).get("other_sources") or [],
                      verification_count=deal.verification_count, rating=prod.rating, review_count=prod.review_count)
    deal.score = res.score
    deal.reference_price_cents = res.reference_price_cents
    deal.reference_kind = res.reference_kind
    deal.discount_pct = res.discount_pct
    deal.score_breakdown = {**res.breakdown, "other_sources": (deal.score_breakdown or {}).get("other_sources") or []}
    if deal.deal_type in (DealType.DEAL, DealType.TOP_DEAL, DealType.PRICE_ERROR_SUSPECT):
        deal.deal_type = DealType(res.deal_type)


class PriceCheckerAgent(Agent):
    name, title = "price_checker", "Preisfehler Hunter & Preisprüfer"
    description = "Bewertet Preise gegen die eigene Historie (Score 0–100) und verifiziert sie erneut."

    def run(self, db: Session, ctx: AgentContext) -> dict:
        t = ctx.clock()
        stats = {"scored": 0, "rejected": 0, "verified": 0, "changed": 0, "expired": 0, "alerts": 0}
        for d in db.scalars(select(Deal).where(Deal.status.in_([S.NEW, S.PRICE_CHANGED]))).all():
            rescore(db, d, t)
            stats["scored"] += 1
            if d.score < 50:
                transition(db, d, S.REJECTED, self.name, f"Score {d.score} < 50")
                stats["rejected"] += 1
            else:
                transition(db, d, S.IN_REVIEW, self.name, f"Score {d.score}")
        # Nachprüfung
        review = db.scalars(select(Deal).where(Deal.status == S.IN_REVIEW)).all()
        by_source: dict[str, list[Deal]] = {}
        for d in review:
            if d.price_checked_at and t - aware(d.price_checked_at) < MIN_RECHECK_GAP:
                continue
            by_source.setdefault(d.product.source, []).append(d)
        for src_name, deals in by_source.items():
            src = ctx.source_for(src_name)
            if src is None or not src.is_configured():
                continue  # z.B. Feed ohne Live-Preis → manuelle Bestätigung im Dashboard
            current = src.fetch_current([d.product.external_id for d in deals])
            for d in deals:
                it = current.get(d.product.external_id)
                outcome = apply_recheck(db, d, it, t, self.name)
                stats[outcome] = stats.get(outcome, 0) + 1
                if outcome == "verified" and d.score >= 85:
                    stats["alerts"] += 1
                    send_alert(f"🚨 {deal_label(d)} (Score {d.score}): {d.product.title[:80]} für "
                               f"{d.current_price_cents/100:.2f} € – {d.product.product_url}")
        return stats


def apply_recheck(db: Session, d: Deal, it: SourceItem | None, t, actor: str) -> str:
    """Ergebnis einer Nachprüfung anwenden. Rückgabe: verified|pending|changed|expired."""
    if it is None or not it.available:
        transition(db, d, S.EXPIRED, actor, "Angebot nicht mehr verfügbar")
        return "expired"
    db.add(PricePoint(product_id=d.product_id, price_cents=it.price_cents, source=it.source, observed_at=t))
    if abs(it.price_cents - d.current_price_cents) > d.current_price_cents * PRICE_TOLERANCE:
        d.current_price_cents = it.price_cents
        d.verification_count = 0
        d.price_checked_at = t
        transition(db, d, S.PRICE_CHANGED, actor, f"Preis jetzt {it.price_cents/100:.2f} €")
        return "changed"
    d.verification_count += 1
    d.price_checked_at = t
    rescore(db, d, t)
    if d.score < 50:
        transition(db, d, S.REJECTED, actor, f"Score nach Prüfung {d.score}")
        return "rejected"
    needed = 2 if d.score >= 85 else 1
    if d.verification_count >= needed:
        transition(db, d, S.VERIFIED, actor, f"{d.verification_count}× verifiziert, Score {d.score}")
        return "verified"
    return "pending"


# ---------------------------------------------------------------- Affiliate
class AffiliateAgent(Agent):
    name, title = "affiliate", "Affiliate-Link Agent"
    description = "Erzeugt Partnerlinks (inkl. Tracking-IDs je Kanal), prüft sie und verhindert Duplikate."

    def run(self, db: Session, ctx: AgentContext) -> dict:
        s = get_settings()
        t = ctx.clock()
        stats = {"links_created": 0, "invalid": 0, "blocked_no_tag": 0}
        for d in db.scalars(select(Deal).where(Deal.status == S.VERIFIED)).all():
            if any(lk.is_valid for lk in d.links):
                continue
            p = d.product
            if p.merchant == "amazon_de":
                if not s.amazon_partner_tag:
                    stats["blocked_no_tag"] += 1
                    continue
                channels = {"default": s.amazon_partner_tag, **s.channel_tracking_ids()}
                for ch, tag in channels.items():
                    if any(lk.channel == ch for lk in d.links):
                        continue
                    try:
                        url = amazon_link(p.external_id, tag, s.amazon_marketplace)
                        issues = validate_amazon_link(url, tag)
                    except AffiliateError as e:
                        url, issues = p.product_url, [str(e)]
                    d.links.append(AffiliateLink(network="amazon", channel=ch, url=url, tracking_id=tag,
                                                 is_valid=not issues, last_checked_at=t,
                                                 check_error="; ".join(issues) or None))
                    stats["links_created" if not issues else "invalid"] += 1
            else:
                # Feeds zugelassener Netzwerke liefern bereits Tracking-Deeplinks
                ok = p.product_url.startswith("https://")
                d.links.append(AffiliateLink(network=p.merchant, channel="default", url=p.product_url,
                                             is_valid=ok, last_checked_at=t, check_error=None if ok else "kein https"))
                stats["links_created" if ok else "invalid"] += 1
        if stats["blocked_no_tag"]:
            log_error(db, "agent:affiliate", "AMAZON_PARTNER_TAG fehlt – Deals warten auf Partnerlinks",
                      level="warning")
        return stats


def link_for(deal: Deal, channel: str = "default") -> AffiliateLink | None:
    valid = [lk for lk in deal.links if lk.is_valid]
    return next((lk for lk in valid if lk.channel == channel), next((lk for lk in valid if lk.channel == "default"), None))


# ---------------------------------------------------------------- Creative
def pick_template(db: Session, rng: random.Random) -> str:
    """Epsilon-Greedy über gelernte Vorlagen-Gewichte (Lernsystem)."""
    weights: dict = get_value(db, "learning.template_weights", {}) or {}
    if not weights or rng.random() < 0.3:
        return rng.choice(TEMPLATES)
    return max(TEMPLATES, key=lambda tpl: weights.get(tpl, 1.0))


def enabled_platforms(db: Session) -> list[str]:
    rows = db.scalars(select(PlatformState).where(PlatformState.enabled.is_(True),
                                                  PlatformState.kill_switch.is_(False))).all()
    return [r.platform for r in rows]


class CreativeAgent(Agent):
    name, title = "creative", "Creative AI Agent"
    description = "Erstellt eigene Grafiken (Post, Story, Pin) und Texte je Kanal – ohne fremde Produktbilder."

    def __init__(self, seed: int | None = None):
        self.rng = random.Random(seed)

    def run(self, db: Session, ctx: AgentContext) -> dict:
        s = get_settings()
        storage = get_storage()
        t = ctx.clock()
        stats = {"deals": 0, "assets": 0, "drafts": 0}
        platforms = enabled_platforms(db)
        for d in db.scalars(select(Deal).where(Deal.status == S.VERIFIED)).all():
            if not link_for(d):
                continue
            transition(db, d, S.MEDIA, self.name)
            stand = fmt_local(aware(d.price_checked_at) or t)
            label = deal_label(d)
            cd = CreativeData(title=d.product.title, price_cents=d.current_price_cents,
                              reference_price_cents=d.reference_price_cents if d.reference_kind == "median_90d" else None,
                              discount_pct=d.discount_pct if d.reference_kind == "median_90d" else None,
                              label=label, category=d.product.category, price_stand=stand,
                              brand=d.product.brand, coupon_code=d.coupon_code)
            tpl = pick_template(db, self.rng)
            assets: dict[str, MediaAsset] = {}
            for kind in ("post", "story", "pin"):
                png = render_png(cd, kind, tpl)
                key = f"deals/{d.id}/{kind}-{tpl}-{d.current_price_cents}.png"
                url = storage.put(key, png, "image/png")
                from app.creative.render import SIZES

                w, h = SIZES[kind]
                a = MediaAsset(deal_id=d.id, kind=kind, template=tpl, storage_key=key, public_url=url, width=w,
                               height=h, license="generated", price_cents_rendered=d.current_price_cents)
                db.add(a)
                assets[kind] = a
                stats["assets"] += 1
            db.flush()
            ci = cap.CaptionInput(title=d.product.title, price_cents=d.current_price_cents,
                                  reference_price_cents=cd.reference_price_cents, discount_pct=cd.discount_pct,
                                  label=label, category=d.product.category, price_stand=stand,
                                  coupon_code=d.coupon_code, editorial_note=d.editorial_note)
            page = f"{s.public_base_url.rstrip('/')}/deals/{d.slug}"
            drafts = []
            for pf in set(platforms) | {"website"}:
                if pf == "instagram":
                    text, var = cap.instagram(ci, rng=self.rng)
                    # Optionaler KI-Feinschliff (Budget-Guard); nur übernehmen, wenn Compliance-Vorprüfung besteht
                    ai = polish_hook(db, {"titel": d.product.title, "kategorie": d.product.category, "label": label,
                                          "preis": cd.price_cents / 100, "marke": d.product.brand})
                    if ai:
                        ai_text, _ = cap.instagram(ci, ai_hook=ai.hook, ai_body=ai.body)
                        probe = comp.check(comp.ComplianceInput(
                            platform="instagram", caption=ai_text, link_url=page, link_valid=True, network=None,
                            price_cents=d.current_price_cents, price_checked_at=d.price_checked_at,
                            discount_pct=d.discount_pct, product_source=d.product.source,
                            confirmed_price_error=d.confirmed_price_error, media_license="generated"), t)
                        if probe.passed:
                            text, var = ai_text, "ai"
                    drafts.append((pf, "post", text, None, assets["post"], var, f"{page}?src=instagram"))
                elif pf == "pinterest":
                    from app.publishers.pinterest import board_for

                    title, text = cap.pinterest(ci)
                    drafts.append((pf, "pin", text, title, assets["pin"], board_for(d.product.category, label),
                                   f"{page}?src=pinterest"))
                elif pf in ("telegram", "whatsapp"):
                    url = f"{page}?src={pf}"
                    drafts.append((pf, "message", cap.short_message(ci, url), None, assets["post"], None, url))
                elif pf == "website":
                    drafts.append((pf, "page", cap.website_text(ci), d.product.title[:200], assets["post"], None, page))
            for pf, fmt, text, title, asset, extra, url in drafts:
                h = content_hash(pf, d.id, d.current_price_cents, fmt)
                if db.scalar(select(Publication.id).where(Publication.platform == pf, Publication.content_hash == h)):
                    continue
                db.add(Publication(deal_id=d.id, platform=pf, format=fmt, status=PS.DRAFT, caption=text, title=title,
                                   link_url=url, media_id=asset.id, template=tpl,
                                   caption_variant=extra if pf == "instagram" else None,
                                   board=extra if pf == "pinterest" else None,
                                   price_cents_at_creation=d.current_price_cents, content_hash=h))
                stats["drafts"] += 1
            stats["deals"] += 1
        return stats


# ---------------------------------------------------------------- Compliance
def compliance_input(pub: Publication, deal: Deal) -> comp.ComplianceInput:
    lk = link_for(deal, pub.platform)
    return comp.ComplianceInput(
        platform=pub.platform.value, caption=pub.caption, link_url=pub.link_url, link_valid=bool(lk),
        network=lk.network if lk else None, price_cents=deal.current_price_cents,
        price_checked_at=deal.price_checked_at, discount_pct=deal.discount_pct, product_source=deal.product.source,
        confirmed_price_error=deal.confirmed_price_error,
        media_license=pub.media.license if pub.media else None,
        media_price_cents=pub.media.price_cents_rendered if pub.media else None,
        valid_until=deal.valid_until, expected_tag=lk.tracking_id if lk else None,
        website_page=pub.platform.value == "website",
    )


def run_compliance(db: Session, pub: Publication, t) -> comp.ComplianceResult:
    res = comp.check(compliance_input(pub, pub.deal), t, get_settings().max_price_age_minutes)
    db.add(ComplianceCheck(deal_id=pub.deal_id, publication_id=pub.id, passed=res.passed,
                           issues=[i.as_dict() for i in res.issues]))
    return res


class ComplianceAgent(Agent):
    name, title = "compliance", "Compliance Agent"
    description = "Prüft Kennzeichnung, Preise, Zeitstempel, Links, Bildrechte und irreführende Angaben."

    def run(self, db: Session, ctx: AgentContext) -> dict:
        t = ctx.clock()
        stats = {"checked": 0, "passed": 0, "failed": 0}
        for d in db.scalars(select(Deal).where(Deal.status == S.MEDIA)).all():
            drafts = [p for p in d.publications if p.status == PS.DRAFT]
            ok = 0
            for p in drafts:
                res = run_compliance(db, p, t)
                stats["checked"] += 1
                if res.passed:
                    ok += 1
                    stats["passed"] += 1
                else:
                    p.status = PS.FAILED
                    p.last_error = "; ".join(i.message for i in res.issues if i.severity == "error")
                    stats["failed"] += 1
            if ok:
                transition(db, d, S.APPROVED, self.name, f"{ok}/{len(drafts)} Entwürfe freigegeben")
            else:
                transition(db, d, S.FAILED, self.name, "Kein Entwurf hat die Compliance-Prüfung bestanden")
        return stats
