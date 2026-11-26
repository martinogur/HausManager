"""Fehlerprotokoll, Alarme und Audit."""
from __future__ import annotations

import logging
import traceback

import httpx
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import AuditLog, ErrorLog

log = logging.getLogger("dealfehler")


def log_error(db: Session, source: str, message: str, *, level: str = "error", context: dict | None = None,
              exc: BaseException | None = None, alert: bool = False) -> ErrorLog:
    ctx = dict(context or {})
    if exc is not None:
        ctx["exception"] = "".join(traceback.format_exception_only(type(exc), exc)).strip()[:2000]
    row = ErrorLog(source=source, level=level, message=message[:4000], context=ctx)
    db.add(row)
    db.flush()
    getattr(log, "warning" if level == "warning" else "error")("%s: %s", source, message)
    if alert:
        send_alert(f"⚠️ {source}: {message}")
    return row


def audit(db: Session, actor: str, action: str, **details) -> None:
    db.add(AuditLog(actor=actor, action=action, details=details))


def send_alert(text: str) -> bool:
    """Alarm an Admin (Telegram-Privatchat und/oder Webhook). Fehler beim Alarm werden nur geloggt."""
    s = get_settings()
    if s.is_test:
        return False
    ok = False
    try:
        if s.telegram_bot_token and s.alert_telegram_chat_id:
            r = httpx.post(
                f"https://api.telegram.org/bot{s.telegram_bot_token}/sendMessage",
                json={"chat_id": s.alert_telegram_chat_id, "text": text[:4000], "disable_web_page_preview": True},
                timeout=10,
            )
            ok = r.is_success
        if s.alert_webhook_url:
            r = httpx.post(s.alert_webhook_url, json={"text": text[:4000]}, timeout=10)
            ok = ok or r.is_success
    except httpx.HTTPError as e:  # Alarmierung darf das System nie blockieren
        log.warning("Alarm konnte nicht gesendet werden: %s", e)
    return ok
