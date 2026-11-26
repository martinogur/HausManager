"""Erststart: Plattform-Zustände anlegen und Admin aus Umgebungsvariablen erzeugen."""
import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.domain.frequency import ensure_platform_states
from app.models import Role, User
from app.security import hash_password

log = logging.getLogger(__name__)


def bootstrap(db: Session) -> None:
    ensure_platform_states(db)
    s = get_settings()
    if s.bootstrap_admin_email and s.bootstrap_admin_password:
        email = s.bootstrap_admin_email.lower()
        if not db.scalar(select(User).where(User.email == email)):
            db.add(User(email=email, password_hash=hash_password(s.bootstrap_admin_password), role=Role.ADMIN))
            log.info("Admin %s angelegt", email)
    db.commit()
