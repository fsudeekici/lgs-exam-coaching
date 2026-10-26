from collections.abc import Callable
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.database import get_db
from app.models import Role, User
from app.services.accounts import awaiting_parent_consent

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

DbSession = Annotated[Session, Depends(get_db)]


def get_current_user(token: Annotated[str, Depends(oauth2_scheme)], db: DbSession) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
        user_id = int(payload["sub"])
        issued_at = float(payload["iat"])
    except (jwt.InvalidTokenError, KeyError, ValueError, TypeError):
        raise unauthorized
    user = db.get(User, user_id)
    # A student whose parent consent was withdrawn is signed out too.
    if user is None or not user.is_active or awaiting_parent_consent(user):
        raise unauthorized
    # A password change or reset signs the user out everywhere.
    if user.password_changed_at is not None and issued_at < user.password_changed_at.timestamp():
        raise unauthorized
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_token_payload(token: Annotated[str, Depends(oauth2_scheme)], user: CurrentUser) -> dict:
    """The claims of the token the (already checked) logged-in user sent."""
    return decode_access_token(token)


TokenPayload = Annotated[dict, Depends(get_token_payload)]


def require_role(*roles: Role) -> Callable[[User], User]:
    """Dependency that only lets users with one of the given roles through.

    The role is read from the database, not the token, so role changes apply immediately.
    The user must also have accepted the KVKK privacy notice.
    """

    def checker(user: CurrentUser) -> User:
        # Nothing beyond the account endpoints works before the privacy notice is accepted.
        if user.kvkk_consent_at is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="KVKK aydınlatma metni onayı gerekli")
        if user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return user

    return checker


require_admin = require_role(Role.admin)
CurrentAdmin = Annotated[User, Depends(require_admin)]


def require_superadmin(admin: CurrentAdmin) -> User:
    """Only the main admin may manage the other admins."""
    if not admin.is_superadmin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Bu işlem yalnızca ana yönetici içindir")
    return admin
