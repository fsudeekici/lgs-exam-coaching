from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError
from sqlalchemy import func, select, update

from app.core.config import Settings, settings
from app.database import SessionLocal
from app.models import LoginAttempt, Role, User
from tests.conftest import PASSWORD, auth, make_user

EMAIL = "ogrenci@test.dev"


def login(client, email=EMAIL, password=PASSWORD):
    return client.post("/api/auth/login", data={"username": email, "password": password})


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


def fail_logins(client, count, email=EMAIL):
    for _ in range(count):
        assert login(client, email, "yanlis-sifre").status_code == 401


# --- login rate limit ---


def test_login_is_blocked_after_too_many_wrong_passwords(client, student):
    fail_logins(client, settings.login_max_attempts)

    blocked = login(client, password="yanlis-sifre")

    assert blocked.status_code == 429
    assert blocked.json()["detail"] == "Çok fazla hatalı deneme. 15 dakika sonra tekrar deneyin."
    assert blocked.headers["Retry-After"] == "900"
    # The right password does not get through either while the block lasts.
    assert login(client).status_code == 429


def test_login_still_works_just_below_the_limit(client, student):
    fail_logins(client, settings.login_max_attempts - 1)

    assert login(client).status_code == 200


def test_successful_login_clears_earlier_failures(client, student):
    fail_logins(client, settings.login_max_attempts - 1)
    assert login(client).status_code == 200

    fail_logins(client, settings.login_max_attempts - 1)

    assert login(client).status_code == 200


def test_block_ends_when_the_failures_are_older_than_the_window(client, student):
    fail_logins(client, settings.login_max_attempts)
    assert login(client).status_code == 429

    with SessionLocal() as db:
        long_ago = datetime.now(timezone.utc) - timedelta(minutes=settings.login_window_minutes + 1)
        db.execute(update(LoginAttempt).values(created_at=long_ago))
        db.commit()

    assert login(client).status_code == 200


def test_block_is_per_email(client, student):
    make_user(Role.student, "ali@test.dev", "Ali Can")
    fail_logins(client, settings.login_max_attempts)

    assert login(client).status_code == 429
    assert login(client, "ali@test.dev").status_code == 200
    # Case and spaces in the email do not get around the block.
    assert login(client, "  OGRENCI@test.dev ").status_code == 429


def test_unknown_emails_are_limited_the_same_way(client):
    fail_logins(client, settings.login_max_attempts, email="yok@test.dev")

    assert login(client, "yok@test.dev").status_code == 429


def test_old_failures_are_cleaned_up(client, student):
    fail_logins(client, 2, email="eski@test.dev")
    with SessionLocal() as db:
        db.execute(update(LoginAttempt).values(created_at=datetime.now(timezone.utc) - timedelta(days=1)))
        db.commit()

    fail_logins(client, 1)

    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(LoginAttempt)) == 1


# --- changing your own password ---


def test_change_own_password(client, student):
    old_token = login(client).json()["access_token"]

    response = client.post(
        "/api/auth/change-password",
        json={"current_password": PASSWORD, "new_password": "yeni-sifre-1"},
        headers=bearer(old_token),
    )

    assert response.status_code == 200
    assert login(client).status_code == 401
    assert login(client, password="yeni-sifre-1").status_code == 200
    # The token that comes back works; the one from before the change does not.
    assert client.get("/api/auth/me", headers=bearer(response.json()["access_token"])).status_code == 200
    assert client.get("/api/auth/me", headers=bearer(old_token)).status_code == 401


@pytest.mark.parametrize("role", [Role.admin, Role.parent])
def test_every_role_can_change_their_password(client, role):
    user = make_user(role, "kisi@test.dev", "Kişi")

    response = client.post(
        "/api/auth/change-password", json={"current_password": PASSWORD, "new_password": "yeni-sifre-1"}, headers=auth(user)
    )

    assert response.status_code == 200
    assert login(client, "kisi@test.dev", "yeni-sifre-1").status_code == 200


def test_change_password_needs_the_current_password(client, student):
    response = client.post(
        "/api/auth/change-password", json={"current_password": "yanlis", "new_password": "yeni-sifre-1"}, headers=auth(student)
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Mevcut şifre hatalı"
    assert login(client).status_code == 200


def test_change_password_validates_the_new_password(client, student):
    headers = auth(student)

    short = client.post("/api/auth/change-password", json={"current_password": PASSWORD, "new_password": "kisa"}, headers=headers)

    assert short.status_code == 422
    assert client.post("/api/auth/change-password", json={"current_password": PASSWORD, "new_password": "x"}).status_code == 401
    assert login(client).status_code == 200


def test_admin_password_reset_signs_the_user_out(client, admin, student):
    old_token = login(client).json()["access_token"]
    assert client.get("/api/auth/me", headers=bearer(old_token)).status_code == 200

    reset = client.patch(f"/api/admin/students/{student.id}", json={"password": "koc-verdi-1"}, headers=admin)

    assert reset.status_code == 200
    assert client.get("/api/auth/me", headers=bearer(old_token)).status_code == 401
    assert login(client).status_code == 401
    assert login(client, password="koc-verdi-1").status_code == 200


def test_admin_can_reset_a_parents_password(client, admin):
    parent = make_user(Role.parent, "veli@test.dev", "Veli")

    client.patch(f"/api/admin/parents/{parent.id}", json={"password": "koc-verdi-1"}, headers=admin)

    assert login(client, "veli@test.dev").status_code == 401
    assert login(client, "veli@test.dev", "koc-verdi-1").status_code == 200


def test_editing_other_fields_does_not_sign_the_user_out(client, admin, student):
    token = login(client).json()["access_token"]

    client.patch(f"/api/admin/students/{student.id}", json={"school": "Yeni Okul"}, headers=admin)

    assert client.get("/api/auth/me", headers=bearer(token)).status_code == 200


# --- KVKK consent ---


@pytest.fixture
def newcomer():
    """A student who has not accepted the privacy notice yet."""
    return make_user(Role.student, "yeni@test.dev", "Yeni Öğrenci", kvkk_consent_at=None)


def consent_time(response):
    """The consent moment in a user response (the time zone it is written in may vary)."""
    return datetime.fromisoformat(response.json()["kvkk_consent_at"])


def test_new_user_has_no_consent_and_is_kept_out(client, newcomer):
    headers = auth(newcomer)

    assert client.get("/api/auth/me", headers=headers).json()["kvkk_consent_at"] is None
    for path in ("/api/student/question-logs", "/api/student/analytics", "/api/student/subjects"):
        response = client.get(path, headers=headers)
        assert response.status_code == 403
        assert response.json()["detail"] == "KVKK aydınlatma metni onayı gerekli"


def test_consent_is_required_for_every_role(client):
    admin = make_user(Role.admin, "admin@test.dev", "Admin", kvkk_consent_at=None)
    parent = make_user(Role.parent, "veli@test.dev", "Veli", kvkk_consent_at=None)

    assert client.get("/api/admin/students", headers=auth(admin)).status_code == 403
    assert client.get("/api/parent/children", headers=auth(parent)).status_code == 403


def test_accepting_the_notice_stores_the_date_and_opens_the_app(client, newcomer):
    headers = auth(newcomer)
    before = datetime.now(timezone.utc)

    response = client.post("/api/auth/consent", headers=headers)

    assert response.status_code == 200
    accepted = consent_time(response)
    assert before <= accepted <= datetime.now(timezone.utc)
    assert consent_time(client.get("/api/auth/me", headers=headers)) == accepted
    assert client.get("/api/student/question-logs", headers=headers).status_code == 200


def test_first_consent_date_is_kept(client, newcomer):
    headers = auth(newcomer)
    first = consent_time(client.post("/api/auth/consent", headers=headers))

    again = consent_time(client.post("/api/auth/consent", headers=headers))

    assert again == first


def test_consent_needs_a_login(client):
    assert client.post("/api/auth/consent").status_code == 401


def test_users_created_by_admin_must_consent_themselves(client, admin):
    created = client.post(
        "/api/admin/students",
        json={
            "full_name": "Elif Yılmaz",
            "email": "elif@test.dev",
            "password": "gizli-sifre",
            "parent_consent_date": "2026-09-01",
        },
        headers=admin,
    ).json()

    with SessionLocal() as db:
        assert db.get(User, created["id"]).kvkk_consent_at is None
    token = login(client, "elif@test.dev", "gizli-sifre").json()["access_token"]
    assert client.get("/api/student/question-logs", headers=bearer(token)).status_code == 403


def test_password_can_be_changed_before_consent(client, newcomer):
    response = client.post(
        "/api/auth/change-password", json={"current_password": PASSWORD, "new_password": "yeni-sifre-1"}, headers=auth(newcomer)
    )

    assert response.status_code == 200


# --- parent consent for students ---

NO_PARENT_CONSENT = "Veli onayı alınmadan giriş yapılamaz. Lütfen koçunuzla iletişime geçin."


@pytest.fixture
def waiting():
    """A student whose parent has not given consent yet."""
    return make_user(Role.student, "bekleyen@test.dev", "Bekleyen Öğrenci", parent_consent_date=None)


def test_student_cannot_log_in_without_parent_consent(client, waiting):
    response = login(client, "bekleyen@test.dev")

    assert response.status_code == 403
    assert response.json()["detail"] == NO_PARENT_CONSENT
    assert "access_token" not in response.json()
    # With a wrong password the answer is the usual one: the account's state is not revealed.
    assert login(client, "bekleyen@test.dev", "yanlis-sifre").status_code == 401


def test_waiting_for_parent_consent_does_not_count_as_failed_logins(client, waiting):
    for _ in range(settings.login_max_attempts + 1):
        assert login(client, "bekleyen@test.dev").status_code == 403


def test_student_can_log_in_once_admin_records_parent_consent(client, admin, waiting):
    listed = client.get("/api/admin/students", headers=admin).json()[0]
    assert listed["parent_consent_date"] is None

    response = client.patch(
        f"/api/admin/students/{waiting.id}", json={"parent_consent_date": "2026-10-01"}, headers=admin
    )

    assert response.json()["parent_consent_date"] == "2026-10-01"
    assert login(client, "bekleyen@test.dev").status_code == 200


def test_student_created_without_parent_consent_cannot_log_in(client, admin):
    created = client.post(
        "/api/admin/students",
        json={"full_name": "Elif Yılmaz", "email": "elif@test.dev", "password": "gizli-sifre"},
        headers=admin,
    )

    assert created.json()["parent_consent_date"] is None
    assert login(client, "elif@test.dev", "gizli-sifre").status_code == 403


def test_removing_parent_consent_signs_the_student_out(client, admin, student):
    token = login(client).json()["access_token"]
    assert client.get("/api/student/question-logs", headers=bearer(token)).status_code == 200

    response = client.patch(f"/api/admin/students/{student.id}", json={"parent_consent_date": None}, headers=admin)

    assert response.json()["parent_consent_date"] is None
    assert client.get("/api/student/question-logs", headers=bearer(token)).status_code == 401
    assert client.get("/api/auth/me", headers=bearer(token)).status_code == 401
    assert login(client).status_code == 403


def test_editing_other_fields_keeps_parent_consent(client, admin, student):
    client.patch(f"/api/admin/students/{student.id}", json={"parent_consent_date": "2026-09-15"}, headers=admin)

    body = client.patch(f"/api/admin/students/{student.id}", json={"school": "Yeni Okul"}, headers=admin).json()

    assert body["parent_consent_date"] == "2026-09-15"


def test_parent_consent_date_cannot_be_in_the_future(client, admin, student):
    tomorrow = (datetime.now().date() + timedelta(days=1)).isoformat()

    response = client.patch(f"/api/admin/students/{student.id}", json={"parent_consent_date": tomorrow}, headers=admin)

    assert response.status_code == 422


def test_parent_consent_only_applies_to_students(client):
    make_user(Role.parent, "veli@test.dev", "Veli")
    make_user(Role.admin, "admin@test.dev", "Admin")

    assert login(client, "veli@test.dev").status_code == 200
    assert login(client, "admin@test.dev").status_code == 200


# --- admin unblocks a login ---


def test_admin_sees_who_is_blocked(client, admin, student):
    other = make_user(Role.student, "ali@test.dev", "Ali Can")
    parent = make_user(Role.parent, "veli@test.dev", "Veli")
    fail_logins(client, settings.login_max_attempts - 1, email="ali@test.dev")
    fail_logins(client, settings.login_max_attempts)
    fail_logins(client, settings.login_max_attempts, email="veli@test.dev")

    students = {s["id"]: s["login_blocked"] for s in client.get("/api/admin/students", headers=admin).json()}
    parents = {p["id"]: p["login_blocked"] for p in client.get("/api/admin/parents", headers=admin).json()}

    assert students == {student.id: True, other.id: False}
    assert parents == {parent.id: True}


def test_admin_unblocks_a_student(client, admin, student):
    fail_logins(client, settings.login_max_attempts)
    assert login(client).status_code == 429

    response = client.post(f"/api/admin/students/{student.id}/unblock-login", headers=admin)

    assert response.status_code == 200
    assert response.json()["login_blocked"] is False
    assert login(client).status_code == 200


def test_admin_unblocks_a_parent(client, admin):
    parent = make_user(Role.parent, "veli@test.dev", "Veli")
    fail_logins(client, settings.login_max_attempts, email="veli@test.dev")

    response = client.post(f"/api/admin/parents/{parent.id}/unblock-login", headers=admin)

    assert response.status_code == 200
    assert login(client, "veli@test.dev").status_code == 200


def test_unblocking_one_user_leaves_others_blocked(client, admin, student):
    make_user(Role.student, "ali@test.dev", "Ali Can")
    fail_logins(client, settings.login_max_attempts)
    fail_logins(client, settings.login_max_attempts, email="ali@test.dev")

    client.post(f"/api/admin/students/{student.id}/unblock-login", headers=admin)

    assert login(client).status_code == 200
    assert login(client, "ali@test.dev").status_code == 429


def test_unblock_is_admin_only_and_checks_the_user(client, admin, student):
    parent = make_user(Role.parent, "veli@test.dev", "Veli")

    assert client.post(f"/api/admin/students/{student.id}/unblock-login", headers=auth(student)).status_code == 403
    assert client.post(f"/api/admin/students/{student.id}/unblock-login").status_code == 401
    assert client.post("/api/admin/students/9999/unblock-login", headers=admin).status_code == 404
    # A parent is not reachable through the student endpoint, and the other way round.
    assert client.post(f"/api/admin/students/{parent.id}/unblock-login", headers=admin).status_code == 404
    assert client.post(f"/api/admin/parents/{student.id}/unblock-login", headers=admin).status_code == 404


def test_admin_edit_reports_block_status(client, admin, student):
    fail_logins(client, settings.login_max_attempts)

    body = client.patch(f"/api/admin/students/{student.id}", json={"school": "Yeni Okul"}, headers=admin).json()

    assert body["login_blocked"] is True


# --- production settings ---

GOOD_SECRET = "x7Qp2mVz9LkR4tYw8NcB6hJd3FgS5aUe1ZoXiCvPqM"


def production(**overrides):
    values = {"environment": "production", "jwt_secret": GOOD_SECRET, "admin_password": "uzun-ve-ozel-1", **overrides}
    return Settings(_env_file=None, **values)


def test_production_settings_accept_strong_secrets():
    assert production().is_production
    assert production(admin_password=None).admin_password is None


@pytest.mark.parametrize(
    "overrides",
    [{"jwt_secret": "change-me"}, {"jwt_secret": "kisa-anahtar"}, {"admin_password": "change-me"}, {"admin_password": "kisa"}],
)
def test_production_settings_refuse_weak_secrets(overrides):
    with pytest.raises(ValidationError):
        production(**overrides)


def test_development_settings_allow_placeholders():
    assert not Settings(_env_file=None, jwt_secret="change-me", admin_password="change-me").is_production
