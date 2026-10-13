from collections.abc import Iterable
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password
from app.models import LoginAttempt, Role, User


def set_password(user: User, password: str) -> None:
    """Change a user's password. Tokens issued before this moment stop working."""
    user.hashed_password = hash_password(password)
    user.password_changed_at = datetime.now(timezone.utc)


def login_window_start() -> datetime:
    return datetime.now(timezone.utc) - timedelta(minutes=settings.login_window_minutes)


def blocked_emails(db: Session) -> set[str]:
    """Emails that cannot log in right now because of too many wrong passwords."""
    return set(
        db.scalars(
            select(LoginAttempt.email)
            .where(LoginAttempt.created_at > login_window_start())
            .group_by(LoginAttempt.email)
            .having(func.count() >= settings.login_max_attempts)
        )
    )


def mark_login_blocked(db: Session, users: Iterable[User]) -> None:
    """Set `login_blocked` on each user, for the admin lists."""
    blocked = blocked_emails(db)
    for user in users:
        user.login_blocked = user.email in blocked


def clear_login_failures(db: Session, email: str) -> None:
    db.execute(delete(LoginAttempt).where(LoginAttempt.email == email))


def awaiting_parent_consent(user: User) -> bool:
    """Students may only use the app once the admin has recorded their parent's consent."""
    return user.role == Role.student and user.parent_consent_date is None
