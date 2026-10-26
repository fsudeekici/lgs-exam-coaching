"""Test setup.

Tests run against a separate PostgreSQL database: TEST_DATABASE_URL if set, otherwise
DATABASE_URL with "_test" appended to the database name. It is created when missing
and brought up to date with Alembic, so the migrations are exercised too.
"""

import os
from collections.abc import Iterator
from datetime import date, datetime, timezone

os.environ.setdefault("JWT_SECRET", "test-secret-only-used-when-none-is-configured")

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, make_url, text

from app.core.config import settings

if os.environ.get("TEST_DATABASE_URL"):
    test_url = make_url(os.environ["TEST_DATABASE_URL"])
else:
    dev_url = make_url(settings.database_url)
    test_url = dev_url.set(database=f"{dev_url.database}_test")
# Tests truncate tables, so never let them near a non-test database.
assert test_url.database.endswith("_test"), "Test database name must end with _test"

# Must happen before app.database is imported, which creates the engine from the settings.
admin_url = make_url(settings.database_url)
settings.database_url = test_url.render_as_string(hide_password=False)

from fastapi.testclient import TestClient

from app.core.security import create_access_token, hash_password
from app.database import SessionLocal, engine
from app.main import app
from app.models import Role, User
from app.seed import seed_subjects

PASSWORD = "test-password"


@pytest.fixture(scope="session", autouse=True)
def database() -> None:
    admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as conn:
        exists = conn.scalar(text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": test_url.database})
        if not exists:
            conn.execute(text(f'CREATE DATABASE "{test_url.database}"'))
    admin_engine.dispose()

    command.upgrade(Config("alembic.ini"), "head")
    with SessionLocal() as db:
        seed_subjects(db)
        db.commit()


@pytest.fixture(autouse=True)
def clean_tables(database: None) -> Iterator[None]:
    yield
    # Subjects and topics are reference data and stay.
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE users, exams, login_attempts RESTART IDENTITY CASCADE"))


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def make_user(role: Role, email: str, full_name: str, **fields) -> User:
    """Create a user who has already accepted the KVKK notice (pass kvkk_consent_at=None for one who has not)."""
    fields.setdefault("kvkk_consent_at", datetime.now(timezone.utc))
    if role == Role.student:
        # ...and whose parent's consent is on record (pass parent_consent_date=None for one without).
        fields.setdefault("parent_consent_date", date.today())
    with SessionLocal() as db:
        user = User(role=role, email=email, full_name=full_name, hashed_password=hash_password(PASSWORD), **fields)
        db.add(user)
        db.commit()
        return user


def auth(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user.id, user.role.value)}"}


@pytest.fixture
def admin() -> dict[str, str]:
    """Auth headers for the main admin, who sees every student."""
    return auth(make_user(Role.admin, "admin@test.dev", "Admin", is_superadmin=True))


@pytest.fixture
def student() -> User:
    return make_user(Role.student, "ogrenci@test.dev", "Ayşe Demir")
