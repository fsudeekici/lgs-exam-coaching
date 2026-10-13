from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import delete, func, select

from app.api.deps import CurrentUser, DbSession, TokenPayload
from app.core.config import settings
from app.core.security import create_access_token, verify_password
from app.models import LoginAttempt, User
from app.schemas.auth import PasswordChange, Token, UserOut
from app.services.accounts import awaiting_parent_consent, clear_login_failures, login_window_start, set_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=Token)
def login(
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    request: Request,
    db: DbSession,
    remember_me: Annotated[bool, Form()] = False,
) -> Token:
    """Log in with email (sent in the OAuth2 `username` field) and password.

    With `remember_me` the session lasts REMEMBER_ME_DAYS instead of ACCESS_TOKEN_EXPIRE_MINUTES.

    After too many wrong passwords for an email, that email is blocked until the oldest
    failures fall out of the window, even if the right password is sent.
    """
    email = form.username.strip().lower()[:255]
    window_start = login_window_start()
    failures = db.scalar(
        select(func.count())
        .select_from(LoginAttempt)
        .where(LoginAttempt.email == email, LoginAttempt.created_at > window_start)
    )
    if failures >= settings.login_max_attempts:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Çok fazla hatalı deneme. {settings.login_window_minutes} dakika sonra tekrar deneyin.",
            headers={"Retry-After": str(settings.login_window_minutes * 60)},
        )

    user = db.scalar(select(User).where(User.email == email))
    if user is None or not user.is_active or not verify_password(form.password, user.hashed_password):
        # Unknown emails are counted too, so the response does not reveal which emails exist.
        db.add(LoginAttempt(email=email, ip=request.client.host if request.client else None))
        db.execute(delete(LoginAttempt).where(LoginAttempt.created_at <= window_start))
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-posta veya şifre hatalı",
            headers={"WWW-Authenticate": "Bearer"},
        )

    clear_login_failures(db, email)
    db.commit()
    # Checked only after the password, so nobody else can learn the state of the account.
    if awaiting_parent_consent(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Veli onayı alınmadan giriş yapılamaz. Lütfen koçunuzla iletişime geçin.",
        )
    return Token(access_token=create_access_token(user.id, user.role.value, remember=remember_me))


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser) -> User:
    return user


@router.post("/consent", response_model=UserOut)
def accept_privacy_notice(user: CurrentUser, db: DbSession) -> User:
    """Record that the user accepted the KVKK privacy notice. The first date is kept."""
    if user.kvkk_consent_at is None:
        user.kvkk_consent_at = datetime.now(timezone.utc)
        db.commit()
    return user


@router.post("/change-password", response_model=Token)
def change_password(payload: PasswordChange, user: CurrentUser, token: TokenPayload, db: DbSession) -> Token:
    """Change your own password. Returns a new token; every older token stops working.

    The new token lasts as long as the one it replaces: a remembered session stays remembered.
    """
    if not verify_password(payload.current_password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Mevcut şifre hatalı")
    set_password(user, payload.new_password)
    db.commit()
    return Token(access_token=create_access_token(user.id, user.role.value, remember=token.get("remember") is True))
