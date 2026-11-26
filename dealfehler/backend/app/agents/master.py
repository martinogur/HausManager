"""CEO / Master Agent: steuert die Pipeline, überwacht Agenten, Kosten und erstellt Berichte."""
from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.agents.base import Agent, AgentContext, run_agent
from app.agents.growth import GrowthAgent
from app.agents.pipeline import AffiliateAgent, ComplianceAgent, CreativeAgent, DealHunterAgent, PriceCheckerAgent
from app.agents.publishing import MasterPriorityAgent, PriceWatchAgent, PublisherAgent, SchedulerAgent
from app.domain.settings_store import get_value
from app.domain.timeutil import local
from app.llm.client import spent_usd
from app.models import AgentState, Click, CostEntry, Deal, ErrorLog, Publication, Report
from app.models import PublicationStatus as PS
from app.ops import send_alert

PIPELINE = [DealHunterAgent, PriceCheckerAgent, AffiliateAgent, CreativeAgent, ComplianceAgent,
            MasterPriorityAgent, SchedulerAgent]
ALL_AGENTS: dict[str, type[Agent]] = {a.name: a for a in [*PIPELINE, PublisherAgent, PriceWatchAgent, GrowthAgent]}


def daily_report(db: Session, day_start: datetime, day_end: datetime) -> dict:
    cnt = lambda model, *where: db.scalar(select(func.count()).select_from(model).where(*where)) or 0  # noqa: E731
    by_platform = dict(db.execute(select(Publication.platform, func.count()).where(
        Publication.status == PS.PUBLISHED, Publication.published_at >= day_start,
        Publication.published_at < day_end).group_by(Publication.platform)).all())
    return {
        "deals_found": cnt(Deal, Deal.created_at >= day_start, Deal.created_at < day_end),
        "price_error_suspects": cnt(Deal, Deal.created_at >= day_start, Deal.created_at < day_end, Deal.score >= 90),
        "published": {k.value if hasattr(k, "value") else k: v for k, v in by_platform.items()},
        "clicks": cnt(Click, Click.created_at >= day_start, Click.created_at < day_end),
        "errors": cnt(ErrorLog, ErrorLog.created_at >= day_start, ErrorLog.created_at < day_end, ErrorLog.level == "error"),
        "cost_usd": round(float(db.scalar(select(func.coalesce(func.sum(CostEntry.cost_usd), 0)).where(
            CostEntry.created_at >= day_start, CostEntry.created_at < day_end)) or 0), 4),
    }


class MasterAgent(Agent):
    name, title = "master", "DEALFEHLER AI – Master Agent"
    description = "Steuert alle Agenten, überwacht Fehler/Kosten, pausiert bei Problemen und erstellt Berichte."

    def run(self, db: Session, ctx: AgentContext) -> dict:
        t = ctx.clock()
        if get_value(db, "global_kill_switch", False):
            return {"skipped": "Globaler Not-Aus aktiv"}
        results = {}
        for cls in PIPELINE:
            agent = cls()
            run = run_agent(db, agent, ctx)
            results[agent.name] = {"status": run.status, **(run.stats or {})}
        # Überwachung
        broken = db.scalars(select(AgentState).where(AgentState.consecutive_failures >= 3)).all()
        if broken:
            send_alert("Agenten mit wiederholten Fehlern: " + ", ".join(b.name for b in broken))
        results["llm_spent_today_usd"] = round(spent_usd(db, "anthropic", 1), 4)
        # Tagesbericht für gestern (einmalig)
        y = (local(t) - timedelta(days=1)).date()
        period = y.isoformat()
        if not db.scalar(select(Report.id).where(Report.kind == "daily", Report.period == period)):
            start = local(t).replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
            db.add(Report(kind="daily", period=period, content=daily_report(db, start, start + timedelta(days=1))))
            results["daily_report"] = period
        return results


def run_cycle(db: Session, ctx: AgentContext) -> dict:
    run = run_agent(db, MasterAgent(), ctx)
    return {"status": run.status, **(run.stats or {})}
