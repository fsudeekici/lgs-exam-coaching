from app.models import Role
from tests.conftest import PASSWORD, auth, make_user

NEW_STUDENT = {
    "full_name": "  Elif Yılmaz ",
    "email": "Elif@Test.dev",
    "password": "gizli-sifre",
    "school": "Atatürk Ortaokulu",
    "class_name": "8-A",
    "parent_consent_date": "2026-09-01",
}


def login(client, email, password):
    return client.post("/api/auth/login", data={"username": email, "password": password})


def test_only_admin_can_manage_users(client, student):
    assert client.get("/api/admin/students").status_code == 401
    assert client.get("/api/admin/students", headers=auth(student)).status_code == 403
    assert client.post("/api/admin/students", json=NEW_STUDENT, headers=auth(student)).status_code == 403
    assert client.get("/api/admin/parents", headers=auth(student)).status_code == 403


def test_create_student(client, admin):
    response = client.post("/api/admin/students", json=NEW_STUDENT, headers=admin)

    assert response.status_code == 201
    body = response.json()
    assert body["full_name"] == "Elif Yılmaz"
    assert body["email"] == "elif@test.dev"
    assert body["school"] == "Atatürk Ortaokulu"
    assert body["class_name"] == "8-A"
    assert body["parent_consent_date"] == "2026-09-01"
    assert body["login_blocked"] is False
    assert body["is_active"] is True
    assert body["parents"] == []
    assert "password" not in body and "hashed_password" not in body

    assert [s["id"] for s in client.get("/api/admin/students", headers=admin).json()] == [body["id"]]
    # The new student can log in, as a student.
    token = login(client, "elif@test.dev", "gizli-sifre").json()["access_token"]
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"}).json()
    assert me["role"] == "student"


def test_create_student_rejects_duplicate_email(client, admin, student):
    response = client.post("/api/admin/students", json={**NEW_STUDENT, "email": "OGRENCI@test.dev"}, headers=admin)

    assert response.status_code == 409
    assert response.json()["detail"] == "Bu e-posta adresi zaten kayıtlı"


def test_create_student_validates_input(client, admin):
    for bad in ({"password": "kisa"}, {"email": "not-an-email"}, {"full_name": "   "}):
        response = client.post("/api/admin/students", json={**NEW_STUDENT, **bad}, headers=admin)
        assert response.status_code == 422, bad


def test_update_student(client, admin, student):
    response = client.patch(
        f"/api/admin/students/{student.id}",
        json={"full_name": "Ayşe Kaya", "school": "Yeni Okul", "class_name": "8-C"},
        headers=admin,
    )

    assert response.status_code == 200
    body = response.json()
    assert (body["full_name"], body["school"], body["class_name"]) == ("Ayşe Kaya", "Yeni Okul", "8-C")
    assert body["email"] == "ogrenci@test.dev"
    # Password was not sent, so it is unchanged.
    assert login(client, "ogrenci@test.dev", PASSWORD).status_code == 200


def test_update_student_can_clear_school_and_class(client, admin):
    student = make_user(Role.student, "s@test.dev", "S", school="Okul", class_name="8-A")

    body = client.patch(f"/api/admin/students/{student.id}", json={"school": "", "class_name": ""}, headers=admin).json()

    assert body["school"] is None and body["class_name"] is None


def test_update_student_password(client, admin, student):
    client.patch(f"/api/admin/students/{student.id}", json={"password": "yeni-sifre-1"}, headers=admin)

    assert login(client, "ogrenci@test.dev", PASSWORD).status_code == 401
    assert login(client, "ogrenci@test.dev", "yeni-sifre-1").status_code == 200


def test_update_student_email_must_be_unique(client, admin, student):
    other = make_user(Role.student, "other@test.dev", "Other")

    taken = client.patch(f"/api/admin/students/{other.id}", json={"email": "ogrenci@test.dev"}, headers=admin)
    same = client.patch(f"/api/admin/students/{other.id}", json={"email": "other@test.dev"}, headers=admin)

    assert taken.status_code == 409
    assert same.status_code == 200


def test_deactivate_and_reactivate_student(client, admin, student):
    headers = auth(student)
    assert client.get("/api/student/dashboard", headers=headers).status_code == 200

    body = client.patch(f"/api/admin/students/{student.id}", json={"is_active": False}, headers=admin).json()

    assert body["is_active"] is False
    # Blocked from logging in, and tokens issued earlier stop working.
    assert login(client, "ogrenci@test.dev", PASSWORD).status_code == 401
    assert client.get("/api/student/dashboard", headers=headers).status_code == 401
    # Still listed, so the admin can reactivate.
    assert [s["is_active"] for s in client.get("/api/admin/students", headers=admin).json()] == [False]

    client.patch(f"/api/admin/students/{student.id}", json={"is_active": True}, headers=admin)
    assert login(client, "ogrenci@test.dev", PASSWORD).status_code == 200


def test_student_endpoints_do_not_touch_other_roles(client, admin):
    parent = make_user(Role.parent, "veli@test.dev", "Veli")

    assert client.patch(f"/api/admin/students/{parent.id}", json={"full_name": "X"}, headers=admin).status_code == 404
    assert client.patch("/api/admin/students/9999", json={"full_name": "X"}, headers=admin).status_code == 404
    assert client.get("/api/admin/students", headers=admin).json() == []


def test_create_parent_linked_to_students(client, admin, student):
    sibling = make_user(Role.student, "kardes@test.dev", "Can Demir")

    response = client.post(
        "/api/admin/parents",
        json={"full_name": "Fatma Demir", "email": "veli@test.dev", "password": "gizli-sifre", "student_ids": [student.id, sibling.id]},
        headers=admin,
    )

    assert response.status_code == 201
    body = response.json()
    assert [s["full_name"] for s in body["students"]] == ["Ayşe Demir", "Can Demir"]
    # The link shows up on the student side too.
    students = {s["id"]: s for s in client.get("/api/admin/students", headers=admin).json()}
    assert students[student.id]["parents"] == [{"id": body["id"], "full_name": "Fatma Demir"}]

    # The new parent can log in, as a parent.
    token = login(client, "veli@test.dev", "gizli-sifre").json()["access_token"]
    assert client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"}).json()["role"] == "parent"


def test_parent_can_only_be_linked_to_students(client, admin):
    other_parent = make_user(Role.parent, "veli2@test.dev", "Veli 2")
    payload = {"full_name": "Veli", "email": "veli@test.dev", "password": "gizli-sifre"}

    for ids in ([other_parent.id], [9999]):
        response = client.post("/api/admin/parents", json={**payload, "student_ids": ids}, headers=admin)
        assert response.status_code == 422
    assert [p["id"] for p in client.get("/api/admin/parents", headers=admin).json()] == [other_parent.id]


def test_update_parent_replaces_linked_students(client, admin, student):
    sibling = make_user(Role.student, "kardes@test.dev", "Can Demir")
    parent = client.post(
        "/api/admin/parents",
        json={"full_name": "Veli", "email": "veli@test.dev", "password": "gizli-sifre", "student_ids": [student.id]},
        headers=admin,
    ).json()

    renamed = client.patch(f"/api/admin/parents/{parent['id']}", json={"full_name": "Fatma Demir"}, headers=admin).json()
    relinked = client.patch(f"/api/admin/parents/{parent['id']}", json={"student_ids": [sibling.id]}, headers=admin).json()
    unlinked = client.patch(f"/api/admin/parents/{parent['id']}", json={"student_ids": []}, headers=admin).json()

    # Leaving student_ids out keeps the links.
    assert [s["id"] for s in renamed["students"]] == [student.id]
    assert [s["id"] for s in relinked["students"]] == [sibling.id]
    assert unlinked["students"] == []
