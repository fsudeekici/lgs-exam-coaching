"""Seed reference data. Safe to run repeatedly.

    python -m app.seed          # LGS subjects + admin account from ADMIN_EMAIL / ADMIN_PASSWORD
    python -m app.seed --demo   # also demo students and a parent (local development only)
"""

import sys

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password
from app.database import SessionLocal
from app.models import ParentStudent, Role, Subject, Topic, User

# (code, name, question_count, topics) in LGS booklet order. Topics follow the 8th grade curriculum.
LGS_SUBJECTS = [
    (
        "turkish",
        "Türkçe",
        20,
        [
            "Sözcükte Anlam",
            "Cümlede Anlam",
            "Paragraf",
            "Deyimler ve Atasözleri",
            "Söz Sanatları",
            "Fiilimsiler",
            "Cümlenin Ögeleri",
            "Fiilde Çatı",
            "Cümle Türleri",
            "Yazım Kuralları",
            "Noktalama İşaretleri",
            "Anlatım Bozuklukları",
            "Metin Türleri",
            "Sözel Mantık ve Görsel Okuma",
        ],
    ),
    (
        "history",
        "İnkılap Tarihi",
        10,
        [
            "Bir Kahraman Doğuyor",
            "Millî Uyanış: Bağımsızlık Yolunda Atılan Adımlar",
            "Millî Bir Destan: Ya İstiklal Ya Ölüm!",
            "Atatürkçülük ve Çağdaşlaşan Türkiye",
            "Demokratikleşme Çabaları",
            "Atatürk Dönemi Türk Dış Politikası",
            "Atatürk'ün Ölümü ve Sonrası",
        ],
    ),
    (
        "religion",
        "Din Kültürü",
        10,
        [
            "Kader İnancı",
            "Zekât ve Sadaka",
            "Din ve Hayat",
            "Hz. Muhammed'in Örnekliği",
            "Kur'an-ı Kerim ve Özellikleri",
        ],
    ),
    (
        "english",
        "İngilizce",
        10,
        [
            "Friendship",
            "Teen Life",
            "In the Kitchen",
            "On the Phone",
            "The Internet",
            "Adventures",
            "Tourism",
            "Chores",
            "Science",
            "Natural Forces",
        ],
    ),
    (
        "math",
        "Matematik",
        20,
        [
            "Çarpanlar ve Katlar",
            "Üslü İfadeler",
            "Kareköklü İfadeler",
            "Veri Analizi",
            "Basit Olayların Olma Olasılığı",
            "Cebirsel İfadeler ve Özdeşlikler",
            "Doğrusal Denklemler",
            "Eşitsizlikler",
            "Üçgenler",
            "Eşlik ve Benzerlik",
            "Dönüşüm Geometrisi",
            "Geometrik Cisimler",
        ],
    ),
    (
        "science",
        "Fen Bilimleri",
        20,
        [
            "Mevsimler ve İklim",
            "DNA ve Genetik Kod",
            "Basınç",
            "Madde ve Endüstri",
            "Basit Makineler",
            "Enerji Dönüşümleri ve Çevre Bilimi",
            "Elektrik Yükleri ve Elektrik Enerjisi",
        ],
    ),
]

DEMO_STUDENTS = [
    ("student@example.com", "Demo Öğrenci"),
    ("student2@example.com", "Elif Yılmaz"),
    ("student3@example.com", "Mert Kaya"),
]
DEMO_PASSWORD = "demo1234"


def seed_subjects(db: Session) -> None:
    """Create or update subjects and add any missing topics. Never deletes topics."""
    existing = {s.code: s for s in db.scalars(select(Subject))}
    for order, (code, name, question_count, topics) in enumerate(LGS_SUBJECTS, start=1):
        subject = existing.get(code)
        if subject is None:
            subject = Subject(code=code)
            db.add(subject)
        subject.name = name
        subject.question_count = question_count
        subject.display_order = order

        current = {t.name for t in subject.topics}
        subject.topics.extend(Topic(name=topic) for topic in topics if topic not in current)


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
            if db.get(ParentStudent, (parent.id, students[0].id)) is None:
                db.add(ParentStudent(parent_id=parent.id, student_id=students[0].id))

        db.commit()
    print("Seed complete")


if __name__ == "__main__":
    main()
