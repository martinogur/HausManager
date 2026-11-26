"""Growth- & Umsatz-Agent: echte Kennzahlen auswerten, Gewichte lernen, Vorschläge machen.

Es werden ausschließlich gemessene Klicks und importierte Provisionen verwendet – keine Schätzwerte
als Umsatz ausgegeben.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.agents.base import Agent, AgentContext
from app.domain import frequency as freq
from app.domain.settings_store import set_value
from app.domain.timeutil import aware, local
from app.models import Click, Commission, Deal, PlatformState, Product, Publication, Report
from app.models import PublicationStatus as PS

PRIOR_PUBS = 3  # Glättung: Kategorien mit wenigen Daten bleiben nahe 1.0


def _smoothed_ratio(clicks: float, pubs: float, global_rate: float) -> float:
    if global_rate <= 0:
        return 1.0
    rate = (clicks + PRIOR_PUBS * global_rate) / (pubs + PRIOR_PUBS)
    return round(max(0.5, min(2.0, rate / global_rate)), 3)


def compute_growth(db: Session, t, days: int = 30) -> dict:
    since = t - timedelta(days=days)
    pubs = db.execute(
        select(Publication.id, Publication.platform, Publication.template, Publication.caption_variant,
               Publication.published_at, Product.category)
        .join(Deal, Deal.id == Publication.deal_id).join(Product, Product.id == Deal.product_id)
        .where(Publication.status == PS.PUBLISHED, Publication.published_at >= since)
    ).all()
    clicks = db.execute(
        select(Click.publication_id, Click.channel, Click.created_at, Product.category)
        .join(Deal, Deal.id == Click.deal_id).join(Product, Product.id == Deal.product_id)
        .where(Click.created_at >= since)
    ).all()
    pub_by_id = {p.id: p for p in pubs}
    n_pubs, n_clicks = len(pubs), len(clicks)
    global_rate = n_clicks / n_pubs if n_pubs else 0.0

    by = lambda key: Counter(getattr(p, key) for p in pubs)  # noqa: E731
    cat_pubs, tpl_pubs = by("category"), by("template")
    cat_clicks, tpl_clicks, var_clicks, ch_clicks, hour_clicks = Counter(), Counter(), Counter(), Counter(), Counter()
    for c in clicks:
        cat_clicks[c.category] += 1
        ch_clicks[c.channel] += 1
        hour_clicks[local(aware(c.created_at)).hour] += 1
        p = pub_by_id.get(c.publication_id)
        if p:
            tpl_clicks[p.template] += 1
            var_clicks[p.caption_variant] += 1

    comm = db.execute(
        select(Product.category, Commission.status, func.sum(Commission.commission_cents), func.count())
        .select_from(Commission).join(Deal, Deal.id == Commission.deal_id).join(Product, Product.id == Deal.product_id)
        .where(Commission.occurred_at >= since).group_by(Product.category, Commission.status)
    ).all()
    comm_by_cat: dict[str, dict] = defaultdict(lambda: {"confirmed_cents": 0, "estimated_cents": 0, "orders": 0})
    for cat, status, cents, cnt in comm:
        key = "confirmed_cents" if status == "confirmed" else "estimated_cents"
        comm_by_cat[cat][key] += int(cents or 0)
        comm_by_cat[cat]["orders"] += cnt

    cat_w = {c: _smoothed_ratio(cat_clicks[c], cat_pubs[c], global_rate) for c in cat_pubs}
    tpl_w = {k: _smoothed_ratio(tpl_clicks[k], tpl_pubs[k], global_rate) for k in tpl_pubs if k}
    best_hours = [h for h, _ in hour_clicks.most_common(4)]

    suggestions = []
    if n_pubs < 20:
        suggestions.append("Noch zu wenige Veröffentlichungen für belastbare Aussagen (< 20 in 30 Tagen).")
    else:
        if cat_w:
            top = max(cat_w, key=cat_w.get)
            low = min(cat_w, key=cat_w.get)
            if cat_w[top] > 1.2:
                suggestions.append(f"Kategorie '{top}' erzielt {cat_w[top]:.1f}× so viele Klicks je Beitrag – stärker priorisieren.")
            if cat_w[low] < 0.8:
                suggestions.append(f"Kategorie '{low}' liegt unter dem Schnitt ({cat_w[low]:.1f}×) – Mindest-Score erhöhen.")
        if tpl_w:
            best_tpl = max(tpl_w, key=tpl_w.get)
            suggestions.append(f"Vorlage '{best_tpl}' funktioniert aktuell am besten.")
        if best_hours:
            suggestions.append("Klickstärkste Stunden: " + ", ".join(f"{h}:00" for h in sorted(best_hours)))
    if not comm:
        suggestions.append("Keine Provisionsdaten importiert – PartnerNet-Bericht regelmäßig importieren.")

    return {
        "period_days": days, "publications": n_pubs, "clicks": n_clicks,
        "clicks_per_publication": round(global_rate, 2),
        "clicks_by_channel": dict(ch_clicks), "publications_by_category": dict(cat_pubs),
        "clicks_by_category": dict(cat_clicks), "commission_by_category": dict(comm_by_cat),
        "category_weights": cat_w, "template_weights": tpl_w,
        "caption_variant_clicks": {str(k): v for k, v in var_clicks.items()},
        "best_hours": best_hours, "suggestions": suggestions,
    }


class GrowthAgent(Agent):
    name, title = "growth", "Growth & Umsatz Agent"
    description = "Analysiert Klicks, Reichweite und Provisionen, lernt Gewichte und baut die Frequenz langsam aus."

    def run(self, db: Session, ctx: AgentContext) -> dict:
        t = ctx.clock()
        g = compute_growth(db, t)
        if g["publications"] >= 20:  # erst ab ausreichender Datenbasis lernen
            set_value(db, "learning.category_weights", g["category_weights"])
            set_value(db, "learning.template_weights", g["template_weights"])
            set_value(db, "learning.best_hours", g["best_hours"])
        ramped = []
        for st in db.scalars(select(PlatformState).where(PlatformState.enabled.is_(True))).all():
            since = t - timedelta(days=7)
            total = db.scalar(select(func.count()).select_from(Publication).where(
                Publication.platform == st.platform, Publication.updated_at >= since,
                Publication.status.in_([PS.PUBLISHED, PS.FAILED]))) or 0
            failed = db.scalar(select(func.count()).select_from(Publication).where(
                Publication.platform == st.platform, Publication.updated_at >= since,
                Publication.status == PS.FAILED)) or 0
            ch_clicks = g["clicks_by_channel"].get(st.platform, 0)
            engagement_ok = total >= 5 and ch_clicks >= total  # mindestens 1 Klick je Beitrag
            if freq.maybe_ramp_up(db, st, t, error_rate=(failed / total if total else 1.0), engagement_ok=engagement_ok):
                ramped.append(f"{st.platform}→{st.daily_limit}")
        g["ramped"] = ramped
        period = local(t).strftime("%Y-%m-%d")
        rep = db.scalar(select(Report).where(Report.kind == "growth", Report.period == period))
        if rep:
            rep.content = g
        else:
            db.add(Report(kind="growth", period=period, content=g))
        return {"publications": g["publications"], "clicks": g["clicks"], "ramped": ramped,
                "suggestions": len(g["suggestions"])}
