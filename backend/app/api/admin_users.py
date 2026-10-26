from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentAdmin, DbSession, require_admin
from app.core.security import hash_password
from app.models import Role, User
from app.schemas.user import (
    ParentCreate,
    ParentOut,
    ParentUpdate,
    StudentCreate,
    StudentOut,
    StudentUpdate,
    UserRef,
)
from app.services.accounts import clear_login_failures, mark_login_blocked, set_password
from app.services.coaching import can_see, parents_of, students_of

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])


def get_user_or_404(db: DbSession, admin: User, user_id: int, role: Role) -> User:
    """A student or parent this admin may see. Others' students look the same as missing ones."""
    user = db.get(User, user_id)
    if user is None or user.role != role or not can_see(admin, user):
        detail = "Öğrenci bulunamadı" if role == Role.student else "Veli bulunamadı"
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)
    return user


def ensure_email_free(db: DbSession, email: str, user_id: int | None = None) -> None:
    owner = db.scalar(select(User).where(User.email == email))
    if owner is not None and owner.id != user_id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Bu e-posta adresi zaten kayıtlı")


def load_students(db: DbSession, admin: User, student_ids: list[int]) -> list[User]:
    students = db.scalars(
        select(User).where(User.id.in_(student_ids), User.role == Role.student, students_of(admin))
    ).all()
    if len(students) != len(set(student_ids)):
        raise HTTPException(status_code=422, detail="Seçilen öğrenci bulunamadı")
    return list(students)


def parent_out(admin: User, parent: User) -> ParentOut:
    """A parent as this admin sees them: children coached by someone else are left out."""
    out = ParentOut.model_validate(parent)
    out.students = [UserRef.model_validate(s) for s in parent.students if can_see(admin, s)]
    return out


def apply_account_fields(db: DbSession, user: User, payload: StudentUpdate | ParentUpdate) -> None:
    """Apply the fields shared by students and parents."""
    if payload.full_name is not None:
        user.full_name = payload.full_name
    if payload.email is not None:
        email = payload.email.lower()
        ensure_email_free(db, email, user.id)
        user.email = email
    if payload.password is not None:
        set_password(user, payload.password)
    if payload.is_active is not None:
        user.is_active = payload.is_active


@router.get("/students", response_model=list[StudentOut])
def list_students(db: DbSession, admin: CurrentAdmin):
    """The admin's students, including deactivated ones. The main admin gets every student."""
    students = db.scalars(
        select(User)
        .where(User.role == Role.student, students_of(admin))
        .options(selectinload(User.parents))
        .order_by(User.full_name, User.id)
    ).all()
    mark_login_blocked(db, students)
    return students


@router.post("/students", response_model=StudentOut, status_code=status.HTTP_201_CREATED)
def create_student(payload: StudentCreate, db: DbSession, admin: CurrentAdmin):
    """A new student belongs to the admin who adds them."""
    email = payload.email.lower()
    ensure_email_free(db, email)
    student = User(
        role=Role.student,
        full_name=payload.full_name,
        email=email,
        hashed_password=hash_password(payload.password),
        school=payload.school or None,
        class_name=payload.class_name or None,
        parent_consent_date=payload.parent_consent_date,
        coach_id=admin.id,
    )
    db.add(student)
    db.commit()
    return student


@router.patch("/students/{student_id}", response_model=StudentOut)
def update_student(student_id: int, payload: StudentUpdate, db: DbSession, admin: CurrentAdmin):
    """Edit a student. Send `is_active: false` to deactivate; their exam results are kept."""
    student = get_user_or_404(db, admin, student_id, Role.student)
    apply_account_fields(db, student, payload)
    if payload.school is not None:
        student.school = payload.school or None
    if payload.class_name is not None:
        student.class_name = payload.class_name or None
    if "parent_consent_date" in payload.model_fields_set:
        student.parent_consent_date = payload.parent_consent_date
    db.commit()
    mark_login_blocked(db, [student])
    return student


@router.post("/students/{student_id}/unblock-login", response_model=StudentOut)
def unblock_student_login(student_id: int, db: DbSession, admin: CurrentAdmin):
    """Lift the block that follows too many wrong passwords."""
    student = get_user_or_404(db, admin, student_id, Role.student)
    clear_login_failures(db, student.email)
    db.commit()
    return student


@router.get("/parents", response_model=list[ParentOut])
def list_parents(db: DbSession, admin: CurrentAdmin):
    """Parents the admin added or whose children they coach. The main admin gets every parent."""
    parents = db.scalars(
        select(User)
        .where(User.role == Role.parent, parents_of(admin))
        .options(selectinload(User.students))
        .order_by(User.full_name, User.id)
    ).all()
    mark_login_blocked(db, parents)
    return [parent_out(admin, parent) for parent in parents]


@router.post("/parents", response_model=ParentOut, status_code=status.HTTP_201_CREATED)
def create_parent(payload: ParentCreate, db: DbSession, admin: CurrentAdmin):
    email = payload.email.lower()
    ensure_email_free(db, email)
    parent = User(
        role=Role.parent,
        full_name=payload.full_name,
        email=email,
        hashed_password=hash_password(payload.password),
        students=load_students(db, admin, payload.student_ids),
        coach_id=admin.id,
    )
    db.add(parent)
    db.commit()
    return parent_out(admin, parent)


@router.patch("/parents/{parent_id}", response_model=ParentOut)
def update_parent(parent_id: int, payload: ParentUpdate, db: DbSession, admin: CurrentAdmin):
    parent = get_user_or_404(db, admin, parent_id, Role.parent)
    apply_account_fields(db, parent, payload)
    if payload.student_ids is not None:
        # Links to children of other coaches are not shown to this admin, so they are kept.
        hidden = [s for s in parent.students if not can_see(admin, s)]
        parent.students = hidden + load_students(db, admin, payload.student_ids)
    db.commit()
    mark_login_blocked(db, [parent])
    return parent_out(admin, parent)


@router.post("/parents/{parent_id}/unblock-login", response_model=ParentOut)
def unblock_parent_login(parent_id: int, db: DbSession, admin: CurrentAdmin):
    parent = get_user_or_404(db, admin, parent_id, Role.parent)
    clear_login_failures(db, parent.email)
    db.commit()
    return parent_out(admin, parent)
