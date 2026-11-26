from collections.abc import Callable

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Role, User
from app.security import decode_token

bearer = HTTPBearer(auto_error=False)
RANK = {Role.VIEWER: 0, Role.EDITOR: 1, Role.ADMIN: 2}


def current_user(cred: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)) -> User:
    if cred is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Nicht angemeldet")
    try:
        payload = decode_token(cred.credentials)
    except jwt.PyJWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token ungültig oder abgelaufen") from None
    user = db.scalar(select(User).where(User.email == payload.get("sub")))
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Benutzer inaktiv")
    return user


def require(role: Role) -> Callable[..., User]:
    def dep(user: User = Depends(current_user)) -> User:
        if RANK[user.role] < RANK[role]:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Keine Berechtigung")
        return user

    return dep


viewer = require(Role.VIEWER)
editor = require(Role.EDITOR)
admin = require(Role.ADMIN)
