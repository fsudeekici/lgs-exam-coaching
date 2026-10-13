"""Seed reference data. Safe to run repeatedly.

    python -m app.seed          # LGS subjects and topics + admin account from ADMIN_EMAIL / ADMIN_PASSWORD
    python -m app.seed --demo   # also demo students, a parent and 4 exams with results (local development only)
"""

import json
import random
import sys
from datetime import date
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password
from app.database import SessionLocal
from app.models import Exam, ExamResult, ExamTopicMistake, Role, Subject, Topic, User

# The only source for LGS subjects and topics, listed in booklet order.
SEED_FILE = Path(__file__).resolve().parent.parent / "seed" / "lgs_topics_seed.json"

DEMO_STUDENTS = [
    ("student@example.com", "Demo Öğrenci"),
    ("student2@example.com", "Elif Yılmaz"),
    ("student3@example.com", "Mert Kaya"),
]
DEMO_PASSWORD = "demo1234"
# (name, date, publisher)
DEMO_EXAMS = [
    ("Demo Deneme 1", date(2026, 9, 5), "Özdebir"),
    ("Demo Deneme 2", date(2026, 9, 19), "Töder"),
    ("Demo Deneme 3", date(2026, 10, 3), "Özdebir"),
    ("Demo Deneme 4", date(2026, 10, 17), "Nartest"),
]


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
        subject.short_name = item["short_name"]
        subject.session = item["session"]
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


def seed_demo_exams(db: Session, students: list[User]) -> None:
    """Create the demo exams with results for every given student. Exams that already exist are left alone.

    Results are made up but repeatable: each student has their own level and improves a
    little from exam to exam, so the analytics pages have something to show.
    """
    rng = random.Random(2026)
    subjects = db.scalars(select(Subject).order_by(Subject.display_order)).all()
    for exam_index, (name, exam_date, publisher) in enumerate(DEMO_EXAMS):
        exists = db.scalar(select(Exam).where(Exam.name == name)) is not None
        exam = Exam(name=name, exam_date=exam_date, publisher=publisher)
        for student_index, student in enumerate(students):
            for subject in subjects:
                questions = subject.question_count
                # Always drawn, even for an existing exam, so later exams get the same numbers either way.
                level = 0.5 + 0.1 * student_index + 0.05 * exam_index + rng.uniform(-0.1, 0.1)
                correct = max(0, min(questions, round(questions * level)))
                wrong = rng.randint(0, min(questions - correct, questions // 4))
                topics = rng.sample(subject.topics, min(wrong, 2, len(subject.topics)))
                if not exists:
                    db.add(
                        ExamResult(
                            exam=exam,
                            student_id=student.id,
                            subject_id=subject.id,
                            correct=correct,
                            wrong=wrong,
                            blank=questions - correct - wrong,
                            topic_mistakes=[ExamTopicMistake(topic_id=topic.id) for topic in topics],
                        )
                    )
        if not exists:
            print(f"Created demo exam: {name}")


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
            seed_demo_exams(db, students)

        db.commit()
    print("Seed complete")


if __name__ == "__main__":
    main()
