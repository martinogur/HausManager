"""Statusmaschine für Deals – erlaubte Übergänge zentral definiert."""
from sqlalchemy.orm import Session

from app.models import Deal, DealEvent
from app.models import DealStatus as S

ALLOWED: dict[S, set[S]] = {
    S.NEW: {S.IN_REVIEW, S.REJECTED, S.EXPIRED, S.FAILED},
    S.IN_REVIEW: {S.VERIFIED, S.REJECTED, S.EXPIRED, S.PRICE_CHANGED, S.FAILED},
    S.VERIFIED: {S.MEDIA, S.IN_REVIEW, S.EXPIRED, S.PRICE_CHANGED, S.FAILED},
    S.MEDIA: {S.APPROVED, S.FAILED, S.EXPIRED, S.PRICE_CHANGED},
    S.APPROVED: {S.SCHEDULED, S.PUBLISHED, S.EXPIRED, S.PRICE_CHANGED, S.FAILED},
    S.SCHEDULED: {S.PUBLISHED, S.EXPIRED, S.PRICE_CHANGED, S.FAILED, S.APPROVED},
    S.PUBLISHED: {S.SCHEDULED, S.EXPIRED, S.PRICE_CHANGED},
    S.PRICE_CHANGED: {S.IN_REVIEW, S.EXPIRED, S.REJECTED},
    S.FAILED: {S.IN_REVIEW, S.EXPIRED},
    S.EXPIRED: {S.IN_REVIEW},  # Angebot kommt zurück
    S.REJECTED: {S.IN_REVIEW},
}


class InvalidTransition(ValueError):
    pass


def transition(db: Session, deal: Deal, to: S, actor: str, note: str | None = None, *, force: bool = False) -> None:
    frm = deal.status
    if frm == to:
        return
    if not force and to not in ALLOWED.get(frm, set()):
        raise InvalidTransition(f"{frm.value} → {to.value} nicht erlaubt")
    deal.status = to
    db.add(DealEvent(deal=deal, from_status=frm.value if frm else None, to_status=to.value, actor=actor, note=note))
