from typing import Any

from sqlalchemy.orm import Session

from app.models import KVSetting


def get_value(db: Session, key: str, default: Any = None) -> Any:
    row = db.get(KVSetting, key)
    return default if row is None else row.value


def set_value(db: Session, key: str, value: Any) -> None:
    row = db.get(KVSetting, key)
    if row is None:
        db.add(KVSetting(key=key, value=value))
    else:
        row.value = value
    db.flush()
