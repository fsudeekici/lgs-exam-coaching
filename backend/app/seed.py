"""Seed reference data. Safe to run repeatedly.

    python -m app.seed          # LGS subjects + admin account from ADMIN_EMAIL / ADMIN_PASSWORD
    python -m app.seed --demo   # also a demo student and parent (local development only)
"""

import sys

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password
from app.database import SessionLocal
from app.models import ParentStudent, Role, Subject, User

# (code, name, question_count) in LGS booklet order.
LGS_SUBJECTS = [
    ("turkish", "Turkish", 20),
    ("history", "History", 10),
    ("religion", "Religion", 10),
    ("english", "English", 10),
    ("math", "Math", 20),
    ("science", "Science", 20),
]

DEMO_PASSWORD = "demo1234"


def seed_subjects(db: Session) -> None:
    existing = {s.code: s for s in db.scalars(select(Subject))}
    for order, (code, name, question_count) in enumerate(LGS_SUBJECTS, start=1):
        subject = existing.get(code)
        if subject is None:
            subject = Subject(code=code)
            db.add(subject)
        subject.name = name
        subject.question_count = question_count
        subject.display_order = order


def get_or_create_user(db: Session, email: str, full_name: str, password: str, role: Role) -> User:
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        user = User(email=email, full_name=full_name, hashed_password=hash_password(password), role=role)
        db.add(user)
        db.flush()
        print(f"Created {role.value}: {email}")
    return user


def main() -> None:
    with SessionLocal() as db:
        seed_subjects(db)

        if settings.admin_password:
            get_or_create_user(db, settings.admin_email.lower(), "Admin", settings.admin_password, Role.admin)
        else:
            print("ADMIN_PASSWORD not set, skipping admin account")

        if "--demo" in sys.argv:
            student = get_or_create_user(db, "student@example.com", "Demo Student", DEMO_PASSWORD, Role.student)
            parent = get_or_create_user(db, "parent@example.com", "Demo Parent", DEMO_PASSWORD, Role.parent)
            if db.get(ParentStudent, (parent.id, student.id)) is None:
                db.add(ParentStudent(parent_id=parent.id, student_id=student.id))

        db.commit()
    print("Seed complete")


if __name__ == "__main__":
    main()
