"""Which students and parents an admin may see.

The main admin (`is_superadmin`) sees everyone. Every other admin is a coach who only sees the
students assigned to them, and the parents they added or whose children they coach.
"""

from sqlalchemy import ColumnElement, select, true
from sqlalchemy.orm import aliased

from app.models import ParentStudent, User


def students_of(admin: User) -> ColumnElement[bool]:
    """Filter on User for the students this admin may see."""
    return true() if admin.is_superadmin else User.coach_id == admin.id


def parents_of(admin: User) -> ColumnElement[bool]:
    """Filter on User for the parents this admin may see."""
    if admin.is_superadmin:
        return true()
    student = aliased(User)
    linked = (
        select(ParentStudent.parent_id)
        .join(student, student.id == ParentStudent.student_id)
        .where(student.coach_id == admin.id)
    )
    return (User.coach_id == admin.id) | User.id.in_(linked)


def can_see(admin: User, user: User) -> bool:
    """Whether the admin may see this student or parent."""
    if admin.is_superadmin or user.coach_id == admin.id:
        return True
    return any(student.coach_id == admin.id for student in user.students)
