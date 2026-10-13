from datetime import datetime, timedelta, timezone

import jwt
import pytest
from pydantic import ValidationError

from app.core.config import Settings, settings
from app.core.security import decode_access_token
from app.models import Role
from tests.conftest import PASSWORD, make_user

EMAIL = "ogrenci@test.dev"
NORMAL = timedelta(minutes=settings.access_token_expire_minutes)
REMEMBERED = timedelta(days=30)


def login(client, email=EMAIL, password=PASSWORD, **form):
    return client.post("/api/auth/login", data={"username": email, "password": password, **form})


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


def lifetime(token):
    """How long the token is valid, from issue to expiry."""
    payload = decode_access_token(token)
    return timedelta(seconds=payload["exp"] - payload["iat"])


def is_close(actual, expected):
    return abs(actual - expected) < timedelta(seconds=2)


def me(client, token):
    return client.get("/api/auth/me", headers=bearer(token))


def change_password(client, token, new_password, current=PASSWORD):
    return client.post(
        "/api/auth/change-password",
        json={"current_password": current, "new_password": new_password},
        headers=bearer(token),
    )


# --- password rule: at least 6 characters, nothing else ---


SIMPLE_PASSWORDS = ["123456", "aaaaaa", "şifrem", "      ", "abc def"]


@pytest.mark.parametrize("password", SIMPLE_PASSWORDS)
def test_admin_can_create_a_student_with_any_6_character_password(client, admin, password):
    payload = {"full_name": "Elif Yılmaz", "email": "elif@test.dev", "password": password, "parent_consent_date": "2026-01-01"}

    assert client.post("/api/admin/students", json=payload, headers=admin).status_code == 201
    assert login(client, "elif@test.dev", password).status_code == 200


def test_admin_can_create_a_parent_with_a_6_character_password(client, admin):
    payload = {"full_name": "Veli", "email": "veli@test.dev", "password": "123456"}

    assert client.post("/api/admin/parents", json=payload, headers=admin).status_code == 201
    assert login(client, "veli@test.dev", "123456").status_code == 200


@pytest.mark.parametrize("password", ["", "12345", "şifre"])
def test_passwords_shorter_than_6_characters_are_refused_on_create(client, admin, password):
    student = {"full_name": "Elif Yılmaz", "email": "elif@test.dev", "password": password}
    parent = {"full_name": "Veli", "email": "veli@test.dev", "password": password}

    assert client.post("/api/admin/students", json=student, headers=admin).status_code == 422
    assert client.post("/api/admin/parents", json=parent, headers=admin).status_code == 422


@pytest.mark.parametrize("password", SIMPLE_PASSWORDS)
def test_user_can_change_to_any_6_character_password(client, student, password):
    token = login(client).json()["access_token"]

    assert change_password(client, token, password).status_code == 200
    assert login(client, password=password).status_code == 200


def test_change_to_a_5_character_password_is_refused(client, student):
    token = login(client).json()["access_token"]

    response = change_password(client, token, "12345")

    assert response.status_code == 422
    assert "en az 6 karakter" in response.text
    assert login(client).status_code == 200


@pytest.mark.parametrize("kind, role", [("students", Role.student), ("parents", Role.parent)])
def test_admin_reset_follows_the_same_rule(client, admin, kind, role):
    user = make_user(role, "kisi@test.dev", "Kişi")
    url = f"/api/admin/{kind}/{user.id}"

    assert client.patch(url, json={"password": "12345"}, headers=admin).status_code == 422
    assert login(client, "kisi@test.dev").status_code == 200
    assert client.patch(url, json={"password": "123456"}, headers=admin).status_code == 200
    assert login(client, "kisi@test.dev", "123456").status_code == 200


def test_password_longer_than_bcrypt_accepts_is_still_refused(client, student):
    token = login(client).json()["access_token"]

    assert change_password(client, token, "a" * 72).status_code == 200
    token = login(client, password="a" * 72).json()["access_token"]
    assert change_password(client, token, "a" * 73, current="a" * 72).status_code == 422


# --- "Beni hatırla" ---


def test_login_without_remember_me_keeps_the_normal_session_time(client, student):
    for form in ({}, {"remember_me": "false"}):
        token = login(client, **form).json()["access_token"]

        assert is_close(lifetime(token), NORMAL)
        assert "remember" not in decode_access_token(token)


def test_login_with_remember_me_lasts_30_days(client, student):
    token = login(client, remember_me="true").json()["access_token"]

    assert settings.remember_me_days == 30
    assert is_close(lifetime(token), REMEMBERED)
    assert me(client, token).status_code == 200


@pytest.mark.parametrize("role", [Role.admin, Role.parent])
def test_remember_me_works_for_every_role(client, role):
    make_user(role, "kisi@test.dev", "Kişi")

    token = login(client, "kisi@test.dev", remember_me="true").json()["access_token"]

    assert is_close(lifetime(token), REMEMBERED)


def test_remember_me_does_not_get_around_the_password_check(client, student):
    assert login(client, password="yanlis-sifre", remember_me="true").status_code == 401


def test_remember_me_does_not_get_around_parent_consent(client):
    make_user(Role.student, "bekleyen@test.dev", "Bekleyen", parent_consent_date=None)

    assert login(client, "bekleyen@test.dev", remember_me="true").status_code == 403


def test_invalid_remember_me_value_is_rejected(client, student):
    assert login(client, remember_me="belki").status_code == 422


def test_remembered_session_ends_after_30_days(client, student):
    """Tokens are only trusted until their expiry: one issued 31 days ago with a 30 day life is refused."""
    issued = datetime.now(timezone.utc) - timedelta(days=31)
    payload = {"sub": str(student.id), "role": "student", "iat": issued.timestamp(), "exp": issued + REMEMBERED, "remember": True}
    expired = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    still_valid = jwt.encode(
        payload | {"exp": issued + timedelta(days=32)}, settings.jwt_secret, algorithm=settings.jwt_algorithm
    )

    assert me(client, expired).status_code == 401
    assert me(client, still_valid).status_code == 200


# --- password change and other sessions ---


def test_password_change_signs_out_remembered_sessions_elsewhere(client, student):
    phone = login(client, remember_me="true").json()["access_token"]
    laptop = login(client).json()["access_token"]

    response = change_password(client, laptop, "yeni-sifre")

    assert response.status_code == 200
    assert me(client, phone).status_code == 401
    assert me(client, laptop).status_code == 401
    assert me(client, response.json()["access_token"]).status_code == 200


def test_password_change_keeps_a_remembered_session_remembered(client, student):
    token = login(client, remember_me="true").json()["access_token"]

    new_token = change_password(client, token, "yeni-sifre").json()["access_token"]

    assert is_close(lifetime(new_token), REMEMBERED)
    assert me(client, new_token).status_code == 200


def test_password_change_keeps_a_normal_session_normal(client, student):
    token = login(client).json()["access_token"]

    new_token = change_password(client, token, "yeni-sifre").json()["access_token"]

    assert is_close(lifetime(new_token), NORMAL)


def test_admin_reset_signs_out_a_remembered_session(client, admin, student):
    token = login(client, remember_me="true").json()["access_token"]

    client.patch(f"/api/admin/students/{student.id}", json={"password": "123456"}, headers=admin)

    assert me(client, token).status_code == 401


def test_deactivating_a_user_ends_a_remembered_session(client, admin, student):
    token = login(client, remember_me="true").json()["access_token"]

    client.patch(f"/api/admin/students/{student.id}", json={"is_active": False}, headers=admin)

    assert me(client, token).status_code == 401


# --- production settings are unchanged ---


def test_production_admin_password_still_needs_8_characters():
    base = {"environment": "production", "jwt_secret": "k9!vQ2#xLm7@pZ4$wN8&rT1*yB6^hD3%", "_env_file": None}

    Settings(**base, admin_password="12345678")
    with pytest.raises(ValidationError):
        Settings(**base, admin_password="1234567")
