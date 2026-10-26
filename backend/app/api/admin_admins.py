from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select

from app.api.admin_users import ensure_email_free
from app.api.deps import DbSession, require_superadmin
from app.core.security import hash_password
from app.models import Role, User
from app.schemas.user import AdminCreate, AdminOut, AdminUpdate
from app.services.accounts import clear_login_failures, mark_login_blocked, set_password

# The main admin adds the other admins (coaches) here. Each coach only sees their own students.
router = APIRouter(prefix="/admin/admins", tags=["admin"])


def get_admin_or_404(db: DbSession, admin_id: int) -> User:
    admin = db.get(User, admin_id)
    if admin is None or admin.role != Role.admin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Yönetici bulunamadı")
    return admin


def admin_out(db: DbSession, admin: User) -> AdminOut:
    mark_login_blocked(db, [admin])
    out = AdminOut.model_validate(admin)
    out.student_count = db.scalar(
        select(func.count()).where(User.coach_id == admin.id, User.role == Role.student, User.is_active)
    )
    return out


@router.get("", response_model=list[AdminOut])
def list_admins(db: DbSession, _: User = Depends(require_superadmin)):
    admins = db.scalars(select(User).where(User.role == Role.admin).order_by(User.full_name, User.id)).all()
    return [admin_out(db, admin) for admin in admins]


@router.post("", response_model=AdminOut, status_code=status.HTTP_201_CREATED)
def create_admin(payload: AdminCreate, db: DbSession, _: User = Depends(require_superadmin)):
    email = payload.email.lower()
    ensure_email_free(db, email)
    admin = User(
        role=Role.admin,
        full_name=payload.full_name,
        email=email,
        hashed_password=hash_password(payload.password),
    )
    db.add(admin)
    db.commit()
    return admin_out(db, admin)


@router.patch("/{admin_id}", response_model=AdminOut)
def update_admin(admin_id: int, payload: AdminUpdate, db: DbSession, me: User = Depends(require_superadmin)):
    """Edit an admin. A deactivated admin cannot log in; their students stay assigned to them."""
    admin = get_admin_or_404(db, admin_id)
    if payload.is_active is False and admin.id == me.id:
        raise HTTPException(status_code=422, detail="Kendi hesabınızı pasifleştiremezsiniz")
    if payload.full_name is not None:
        admin.full_name = payload.full_name
    if payload.email is not None:
        email = payload.email.lower()
        ensure_email_free(db, email, admin.id)
        admin.email = email
    if payload.password is not None:
        set_password(admin, payload.password)
    if payload.is_active is not None:
        admin.is_active = payload.is_active
    db.commit()
    return admin_out(db, admin)


@router.post("/{admin_id}/unblock-login", response_model=AdminOut)
def unblock_admin_login(admin_id: int, db: DbSession, _: User = Depends(require_superadmin)):
    admin = get_admin_or_404(db, admin_id)
    clear_login_failures(db, admin.email)
    db.commit()
    return admin_out(db, admin)
