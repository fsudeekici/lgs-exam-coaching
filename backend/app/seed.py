"""Seed reference data. Safe to run repeatedly.

    python -m app.seed          # LGS subjects and topics + admin account from ADMIN_EMAIL / ADMIN_PASSWORD
    python -m app.seed --demo   # also demo students and a parent (local development only)
"""

import json
import sys
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password
from app.database import SessionLocal
from app.models import ExamTopicMistake, Role, Subject, Topic, User

# The only source for LGS subjects and topics, listed in booklet order.
SEED_FILE = Path(__file__).resolve().parent.parent / "seed" / "lgs_topics_seed.json"

DEMO_STUDENTS = [
    ("student@example.com", "Demo Öğrenci"),
    ("student2@example.com", "Elif Yılmaz"),
    ("student3@example.com", "Mert Kaya"),
]
DEMO_PASSWORD = "demo1234"


def seed_subjects(db: Session) -> None:
    """Make subjects and topics match the seed file.

    Topics missing from the file are deleted, unless a recorded exam mistake still points at them.
    """
    data = json.loads(SEED_FILE.read_text(encoding="utf-8"))
    existing = {s.code: s for s in db.scalars(select(Subject))}
    for order, item in enumerate(data["subjects"], start=1):
        subject = existing.get(item["code"])
        if subject is None:
            subject = Subject(code=item["code"])
            db.add(subject)
        subject.name = item["name"]
        subject.question_count = item["question_count"]
        subject.display_order = order

        current = {t.name for t in subject.topics}
        subject.topics.extend(Topic(name=name) for name in item["topics"] if name not in current)

        for topic in [t for t in subject.topics if t.name not in item["topics"]]:
            in_use = db.scalar(select(ExamTopicMistake).where(ExamTopicMistake.topic_id == topic.id).limit(1))
            if in_use is None:
                subject.topics.remove(topic)
            else:
                print(f"Kept topic not in seed file (used by exam results): {subject.name} / {topic.name}")


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
            students = [
                get_or_create_user(db, email, full_name, DEMO_PASSWORD, Role.student)
                for email, full_name in DEMO_STUDENTS
            ]
            parent = get_or_create_user(db, "parent@example.com", "Demo Veli", DEMO_PASSWORD, Role.parent)
            if students[0] not in parent.students:
                parent.students.append(students[0])

        db.commit()
    print("Seed complete")


if __name__ == "__main__":
    main()
