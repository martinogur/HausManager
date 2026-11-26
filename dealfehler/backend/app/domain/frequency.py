"""Frequenzmanagement: eigene, konservative Limits je Plattform + Not-Aus + langsamer Ausbau.

Es werden bewusst KEINE vermeintlichen Plattform-Maxima angenommen. Die Limits sind eigene
Obergrenzen, die nur bei guter Qualität (keine Fehler, positive Interaktion) erhöht werden.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.settings_store import get_value
from app.domain.timeutil import aware, local
from app.models import PlatformState, Publication, PublicationStatus

DEFAULTS: dict[str, dict] = {
    # konservativer Start; Ausbau über ramp_step je Woche bis daily_limit_max
    "instagram": dict(daily_limit=3, daily_limit_max=12, min_interval_minutes=120, min_score=65),
    "pinterest": dict(daily_limit=5, daily_limit_max=25, min_interval_minutes=45, min_score=55),
    "telegram": dict(daily_limit=8, daily_limit_max=30, min_interval_minutes=30, min_score=60),
    "whatsapp": dict(daily_limit=3, daily_limit_max=10, min_interval_minutes=120, min_score=75,
                     requires_manual_approval=True),
    "website": dict(daily_limit=200, daily_limit_max=500, min_interval_minutes=0, min_score=50,
                    quiet_hours_start=0, quiet_hours_end=0),
    "newsletter": dict(daily_limit=1, daily_limit_max=1, min_interval_minutes=600, min_score=60,
                       requires_manual_approval=True),
}


def ensure_platform_states(db: Session) -> None:
    for name, cfg in DEFAULTS.items():
        if db.get(PlatformState, name) is None:
            db.add(PlatformState(platform=name, enabled=(name == "website"), **cfg))
    db.flush()


@dataclass
class Decision:
    allowed: bool
    reason: str = ""
    next_possible_at: datetime | None = None


def _in_quiet_hours(st: PlatformState, t: datetime) -> bool:
    if st.quiet_hours_start == st.quiet_hours_end:
        return False
    h = local(t).hour
    if st.quiet_hours_start > st.quiet_hours_end:
        return h >= st.quiet_hours_start or h < st.quiet_hours_end
    return st.quiet_hours_start <= h < st.quiet_hours_end


def published_last_24h(db: Session, platform: str, t: datetime) -> int:
    return db.scalar(
        select(func.count()).select_from(Publication).where(
            Publication.platform == platform,
            Publication.status.in_([PublicationStatus.PUBLISHED, PublicationStatus.PUBLISHING]),
            Publication.published_at >= t - timedelta(hours=24),
        )
    ) or 0


def last_published_at(db: Session, platform: str) -> datetime | None:
    return aware(db.scalar(
        select(func.max(Publication.published_at)).where(Publication.platform == platform)
    ))


def can_publish(db: Session, platform: str, t: datetime) -> Decision:
    if get_value(db, "global_kill_switch", False):
        return Decision(False, "Globaler Not-Aus aktiv")
    st = db.get(PlatformState, platform)
    if st is None:
        return Decision(False, "Plattform unbekannt")
    if st.kill_switch:
        return Decision(False, "Not-Aus für Plattform aktiv")
    if not st.enabled:
        return Decision(False, "Plattform deaktiviert")
    if st.paused_until and aware(st.paused_until) > t:
        return Decision(False, f"Pausiert: {st.pause_reason or ''}".strip(), aware(st.paused_until))
    if _in_quiet_hours(st, t):
        return Decision(False, "Ruhezeit")
    n = published_last_24h(db, platform, t)
    if n >= st.daily_limit:
        return Decision(False, f"Tageslimit erreicht ({n}/{st.daily_limit})")
    last = last_published_at(db, platform)
    if last and st.min_interval_minutes and t - last < timedelta(minutes=st.min_interval_minutes):
        return Decision(False, "Mindestabstand", last + timedelta(minutes=st.min_interval_minutes))
    return Decision(True)


def next_slot(db: Session, platform: str, after: datetime, taken: list[datetime] | None = None) -> datetime:
    """Nächster freier Zeitpunkt unter Beachtung von Mindestabstand und Ruhezeiten."""
    st = db.get(PlatformState, platform)
    assert st is not None
    interval = timedelta(minutes=max(st.min_interval_minutes, 1))
    taken = sorted(aware(x) for x in (taken or []))
    last = last_published_at(db, platform)
    candidates = [after]
    if last:
        candidates.append(last + interval)
    t = max(candidates)
    for _ in range(24 * 12):
        clash = any(abs((t - x).total_seconds()) < interval.total_seconds() for x in taken)
        if not clash and not _in_quiet_hours(st, t):
            return t
        t += timedelta(minutes=5) if not clash else interval
    return t


def register_error(db: Session, platform: str, message: str, t: datetime, *, rate_limited: bool = False,
                   retry_after_s: int | None = None) -> PlatformState:
    """Automatische Pause bei API-Fehlern/Warnungen."""
    st = db.get(PlatformState, platform)
    assert st is not None
    st.consecutive_errors += 1
    if rate_limited:
        st.paused_until = t + timedelta(seconds=retry_after_s or 3600)
        st.pause_reason = f"Rate-Limit: {message[:200]}"
    elif st.consecutive_errors >= st.max_consecutive_errors:
        st.paused_until = t + timedelta(hours=6)
        st.pause_reason = f"{st.consecutive_errors} Fehler in Folge: {message[:200]}"
    return st


def register_success(db: Session, platform: str) -> None:
    st = db.get(PlatformState, platform)
    if st:
        st.consecutive_errors = 0


def maybe_ramp_up(db: Session, st: PlatformState, t: datetime, *, error_rate: float, engagement_ok: bool) -> bool:
    """Langsamer Ausbau: höchstens einmal pro 7 Tage, nur ohne Fehler und mit guter Resonanz."""
    if st.daily_limit >= st.daily_limit_max:
        return False
    if st.last_ramp_at and t - aware(st.last_ramp_at) < timedelta(days=7):
        return False
    if error_rate > 0.02 or not engagement_ok:
        return False
    st.daily_limit = min(st.daily_limit + st.ramp_step, st.daily_limit_max)
    st.last_ramp_at = t
    return True
