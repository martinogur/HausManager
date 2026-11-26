from datetime import timedelta

import bcrypt
import jwt

from app.config import get_settings
from app.domain.timeutil import now


def hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()


def verify_password(pw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(pw.encode(), hashed.encode())
    except ValueError:
        return False


def create_token(sub: str, role: str) -> str:
    s = get_settings()
    t = now()
    payload = {"sub": sub, "role": role, "iat": t, "exp": t + timedelta(minutes=s.access_token_minutes)}
    return jwt.encode(payload, s.secret_key, algorithm="HS256")


def decode_token(token: str) -> dict:
    return jwt.decode(token, get_settings().secret_key, algorithms=["HS256"])
