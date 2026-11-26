"""Basis für alle Agenten: Laufprotokoll, Pause, Fehlerisolation, Alarmierung."""
from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy.orm import Session

from app.domain.timeutil import now
from app.models import AgentRun, AgentState
from app.ops import log_error, send_alert
from app.publishers.base import Publisher
from app.sources.base import DealSource

log = logging.getLogger(__name__)
MAX_FAILURES_BEFORE_PAUSE = 5


@dataclass
class AgentContext:
    sources: dict[str, DealSource] = field(default_factory=dict)
    publisher_factory: Callable[[str], Publisher] | None = None
    clock: Callable[[], datetime] = now

    def publisher(self, platform: str) -> Publisher:
        if self.publisher_factory:
            return self.publisher_factory(platform)
        from app.publishers.messaging import get_publisher

        return get_publisher(platform)

    def source_for(self, name: str) -> DealSource | None:
        return self.sources.get(name)


class Agent:
    name: str = "base"
    title: str = ""
    description: str = ""

    def run(self, db: Session, ctx: AgentContext) -> dict:
        raise NotImplementedError


def _state(db: Session, name: str) -> AgentState:
    st = db.get(AgentState, name)
    if st is None:
        st = AgentState(name=name, enabled=True)
        db.add(st)
        db.commit()
    return st


def run_agent(db: Session, agent: Agent, ctx: AgentContext, *, force: bool = False) -> AgentRun:
    """Führt einen Agenten aus. Jeder Agent committet seine Arbeit; Fehler werden zurückgerollt und
    protokolliert, ohne andere Agenten zu beeinflussen."""
    db.expire_all()  # frischer Datenstand (API und andere Worker schreiben parallel)
    st = _state(db, agent.name)
    started = ctx.clock()
    if not st.enabled and not force:
        run = AgentRun(agent=agent.name, status="skipped", started_at=started, finished_at=started)
        db.add(run)
        db.commit()
        return run
    stats, error = {}, None
    try:
        stats = agent.run(db, ctx) or {}
        db.commit()
    except Exception as e:  # Fehlerisolation: ein Agent darf die anderen nicht stoppen
        db.rollback()
        log.exception("Agent %s fehlgeschlagen", agent.name)
        error = f"{type(e).__name__}: {e}"[:4000]
        log_error(db, f"agent:{agent.name}", error, exc=e)
    st = _state(db, agent.name)
    run = AgentRun(agent=agent.name, status="error" if error else "ok", stats=stats, error=error,
                   started_at=started, finished_at=ctx.clock())
    db.add(run)
    if error:
        st.consecutive_failures += 1
        st.last_error = error
        if st.consecutive_failures >= MAX_FAILURES_BEFORE_PAUSE:
            st.enabled = False
            send_alert(f"Agent {agent.name} nach {st.consecutive_failures} Fehlern pausiert: {error[:300]}")
    else:
        st.consecutive_failures, st.last_error = 0, None
    st.last_run_at, st.last_status = run.finished_at, run.status
    st.run_count += 1
    db.commit()
    return run
