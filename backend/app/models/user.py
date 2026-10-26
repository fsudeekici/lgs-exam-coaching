import enum
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Role(str, enum.Enum):
    admin = "admin"
    student = "student"
    parent = "parent"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255))
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[Role] = mapped_column(Enum(Role, name="user_role"))
    is_active: Mapped[bool] = mapped_column(default=True, server_default="true")
    # Only for admins: the main admin manages the other admins and sees every student and parent.
    is_superadmin: Mapped[bool] = mapped_column(default=False, server_default="false")
    # For students and parents: the admin (coach) they belong to. Other coaches cannot see them.
    coach_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    # When the user accepted the KVKK privacy notice; empty until their first login.
    kvkk_consent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Set on every password change; older tokens are rejected.
    password_changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Only used for students.
    school: Mapped[str | None] = mapped_column(String(255))
    class_name: Mapped[str | None] = mapped_column(String(50))
    # The day the admin received the parent's consent. A student cannot log in while this is empty.
    parent_consent_date: Mapped[date | None] = mapped_column(Date)

    coach: Mapped["User | None"] = relationship(remote_side=[id], foreign_keys=[coach_id])

    # Parent -> their students, and student -> their parents, through parent_student.
    students: Mapped[list["User"]] = relationship(
        secondary="parent_student",
        primaryjoin="User.id == ParentStudent.parent_id",
        secondaryjoin="User.id == ParentStudent.student_id",
        back_populates="parents",
        order_by="User.full_name",
    )
    parents: Mapped[list["User"]] = relationship(
        secondary="parent_student",
        primaryjoin="User.id == ParentStudent.student_id",
        secondaryjoin="User.id == ParentStudent.parent_id",
        back_populates="students",
        order_by="User.full_name",
    )


class ParentStudent(Base):
    """Links a parent user to a student user. Role checks happen in the API layer."""

    __tablename__ = "parent_student"

    parent_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True, index=True
    )


class LoginAttempt(Base):
    """A failed login, kept for a short while to block password guessing."""

    __tablename__ = "login_attempts"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), index=True)
    ip: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
