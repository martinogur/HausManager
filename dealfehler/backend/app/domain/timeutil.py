from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from app.config import get_settings


def now() -> datetime:
    return datetime.now(UTC)


def aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def local(dt: datetime) -> datetime:
    return aware(dt).astimezone(ZoneInfo(get_settings().timezone))


def fmt_local(dt: datetime) -> str:
    return local(dt).strftime("%d.%m.%Y, %H:%M Uhr")


def fmt_eur(cents: int) -> str:
    euros = cents / 100
    s = f"{euros:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{s} €"
