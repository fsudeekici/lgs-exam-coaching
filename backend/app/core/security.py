from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.core.config import settings


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed_password.encode())


def create_access_token(user_id: int, role: str, remember: bool = False) -> str:
    """`remember` gives the long "Beni hatırla" lifetime instead of the normal one."""
    now = datetime.now(timezone.utc)
    lifetime = (
        timedelta(days=settings.remember_me_days)
        if remember
        else timedelta(minutes=settings.access_token_expire_minutes)
    )
    # iat keeps sub-second precision so tokens from before a password change can be told apart.
    payload = {"sub": str(user_id), "role": role, "iat": now.timestamp(), "exp": now + lifetime}
    if remember:
        payload["remember"] = True
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    """Raises jwt.InvalidTokenError if the token is invalid or expired."""
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
