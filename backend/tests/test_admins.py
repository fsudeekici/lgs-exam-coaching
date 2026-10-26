import pytest

from app.models import Role
from tests.conftest import auth, make_user
from tests.test_analytics import enter, subjects  # noqa: F401 (fixtures)

NEW_ADMIN = {"full_name": "Koç Ali", "email": "Ali@Test.dev", "password": "koc-sifre"}


def login(client, email, password):
    return client.post("/api/auth/login", data={"username": email, "password": password})


@pytest.fixture
def coach():
    return make_user(Role.admin, "koc1@test.dev", "Koç Bir")


@pytest.fixture
def other_coach():
    return make_user(Role.admin, "koc2@test.dev", "Koç İki")


@pytest.fixture
def own_student(coach):
    return make_user(Role.student, "kendi@test.dev", "Kendi Öğrencisi", coach_id=coach.id)


@pytest.fixture
def others_student(other_coach):
    return make_user(Role.student, "baskasi@test.dev", "Başka Öğrenci", coach_id=other_coach.id)


def ids(response):
    assert response.status_code == 200, response.text
    return [item["id"] for item in response.json()]


# Managing admins


def test_me_says_who_is_the_main_admin(client, admin, coach):
    assert client.get("/api/auth/me", headers=admin).json()["is_superadmin"] is True
    assert client.get("/api/auth/me", headers=auth(coach)).json()["is_superadmin"] is False


def test_main_admin_adds_an_admin_who_can_log_in(client, admin):
    response = client.post("/api/admin/admins", json=NEW_ADMIN, headers=admin)

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "ali@test.dev"
    assert body["is_superadmin"] is False
    assert body["student_count"] == 0
    assert "hashed_password" not in body

    token = login(client, "ali@test.dev", "koc-sifre").json()["access_token"]
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"}).json()
    assert me["role"] == "admin"
    # Like everyone else, the new admin first accepts the KVKK notice.
    assert me["kvkk_consent_at"] is None


def test_admin_list_counts_active_students(client, admin, coach, own_student):
    make_user(Role.student, "pasif@test.dev", "Pasif", coach_id=coach.id, is_active=False)

    admins = {a["email"]: a for a in client.get("/api/admin/admins", headers=admin).json()}

    assert admins["koc1@test.dev"]["student_count"] == 1
    assert admins["admin@test.dev"]["is_superadmin"] is True


def test_only_main_admin_manages_admins(client, coach, student):
    assert client.get("/api/admin/admins", headers=auth(coach)).status_code == 403
    assert client.post("/api/admin/admins", json=NEW_ADMIN, headers=auth(coach)).status_code == 403
    assert client.patch(f"/api/admin/admins/{coach.id}", json={"full_name": "X"}, headers=auth(coach)).status_code == 403
    assert client.get("/api/admin/admins", headers=auth(student)).status_code == 403


def test_add_admin_rejects_duplicate_email(client, admin, student):
    response = client.post("/api/admin/admins", json={**NEW_ADMIN, "email": "OGRENCI@test.dev"}, headers=admin)
    assert response.status_code == 409


def test_deactivated_admin_cannot_log_in(client, admin, coach):
    response = client.patch(f"/api/admin/admins/{coach.id}", json={"is_active": False}, headers=admin)

    assert response.status_code == 200
    assert response.json()["is_active"] is False
    assert client.get("/api/admin/students", headers=auth(coach)).status_code == 401


def test_main_admin_cannot_deactivate_themselves(client, admin):
    me = client.get("/api/auth/me", headers=admin).json()
    response = client.patch(f"/api/admin/admins/{me['id']}", json={"is_active": False}, headers=admin)
    assert response.status_code == 422


def test_editing_a_non_admin_as_admin_is_not_found(client, admin, student):
    assert client.patch(f"/api/admin/admins/{student.id}", json={"full_name": "X"}, headers=admin).status_code == 404


# Each coach sees only their own students


def test_coach_lists_only_own_students(client, admin, coach, own_student, others_student, student):
    assert ids(client.get("/api/admin/students", headers=auth(coach))) == [own_student.id]
    # The main admin sees everyone, including students without a coach.
    assert set(ids(client.get("/api/admin/students", headers=admin))) == {
        own_student.id,
        others_student.id,
        student.id,
    }


def test_student_added_by_coach_belongs_to_them(client, coach, other_coach):
    response = client.post(
        "/api/admin/students",
        json={"full_name": "Yeni", "email": "yeni@test.dev", "password": "gizli-sifre"},
        headers=auth(coach),
    )

    assert response.status_code == 201
    assert ids(client.get("/api/admin/students", headers=auth(coach))) == [response.json()["id"]]
    assert ids(client.get("/api/admin/students", headers=auth(other_coach))) == []


@pytest.mark.parametrize(
    "method, path",
    [
        ("patch", "/api/admin/students/{id}"),
        ("post", "/api/admin/students/{id}/unblock-login"),
        ("get", "/api/admin/students/{id}/analytics"),
        ("get", "/api/admin/students/{id}/question-logs"),
        ("get", "/api/admin/students/{id}/topic-progress"),
        ("get", "/api/admin/students/{id}/notes"),
        ("post", "/api/admin/students/{id}/notes"),
        ("get", "/api/admin/students/{id}/meeting"),
        ("post", "/api/admin/students/{id}/meeting-notes"),
    ],
)
def test_coach_cannot_open_another_coachs_student(client, coach, others_student, method, path):
    body = {"body": "Not", "visible_to_parent": False, "meeting_date": "2026-10-01"}
    kwargs = {"json": body} if method in ("patch", "post") else {}
    response = getattr(client, method)(path.format(id=others_student.id), headers=auth(coach), **kwargs)
    assert response.status_code == 404


def test_coach_cannot_change_another_coachs_notes(client, admin, coach, others_student):
    note = client.post(
        f"/api/admin/students/{others_student.id}/notes", json={"body": "Not", "visible_to_parent": True}, headers=admin
    ).json()
    meeting_note = client.post(
        f"/api/admin/students/{others_student.id}/meeting-notes",
        json={"meeting_date": "2026-10-01", "body": "Görüşme"},
        headers=admin,
    ).json()

    assert client.patch(f"/api/admin/notes/{note['id']}", json={"body": "X"}, headers=auth(coach)).status_code == 404
    assert client.delete(f"/api/admin/notes/{note['id']}", headers=auth(coach)).status_code == 404
    assert client.delete(f"/api/admin/meeting-notes/{meeting_note['id']}", headers=auth(coach)).status_code == 404


def test_overview_shows_only_own_students(client, admin, coach, own_student, others_student):
    rows = client.get("/api/admin/overview", headers=auth(coach)).json()
    assert [row["student_id"] for row in rows] == [own_student.id]
    assert len(client.get("/api/admin/overview", headers=admin).json()) == 2


# Exams are shared, results are not


def test_exams_are_shared_but_results_are_per_coach(client, admin, coach, own_student, others_student, enter):
    exam_id = enter(own_student, "2026-10-01", [5] * 6)
    enter(others_student, "2026-10-01", [8] * 6, exam_id=exam_id)

    exams = client.get("/api/admin/exams", headers=auth(coach)).json()
    assert [(e["id"], e["student_count"]) for e in exams] == [(exam_id, 1)]
    assert client.get("/api/admin/exams", headers=admin).json()[0]["student_count"] == 2

    detail = client.get(f"/api/admin/exams/{exam_id}", headers=auth(coach)).json()
    assert [s["student_id"] for s in detail["students"]] == [own_student.id]
    assert detail["student_count"] == 1


def test_coach_cannot_enter_or_delete_another_coachs_results(
    client, admin, coach, others_student, enter, subjects
):
    exam_id = enter(others_student, "2026-10-01", [5] * 6)
    results = [
        {"subject_id": s["id"], "correct": 0, "wrong": 0, "blank": s["question_count"], "mistake_topic_ids": []}
        for s in subjects
    ]
    path = f"/api/admin/exams/{exam_id}/students/{others_student.id}/results"

    assert client.put(path, json={"results": results}, headers=auth(coach)).status_code == 404
    assert client.delete(path, headers=auth(coach)).status_code == 404
    assert client.get(f"/api/admin/exams/{exam_id}", headers=admin).json()["student_count"] == 1


# Parents


def test_coach_sees_parents_of_own_students_only(client, admin, coach, own_student, others_student):
    own_parent = client.post(
        "/api/admin/parents",
        json={"full_name": "Veli A", "email": "a@test.dev", "password": "gizli-sifre", "student_ids": [own_student.id]},
        headers=admin,
    ).json()
    client.post(
        "/api/admin/parents",
        json={"full_name": "Veli B", "email": "b@test.dev", "password": "gizli-sifre", "student_ids": [others_student.id]},
        headers=admin,
    )

    assert ids(client.get("/api/admin/parents", headers=auth(coach))) == [own_parent["id"]]


def test_parent_added_by_coach_without_students_stays_visible(client, coach, other_coach):
    created = client.post(
        "/api/admin/parents",
        json={"full_name": "Veli", "email": "v@test.dev", "password": "gizli-sifre"},
        headers=auth(coach),
    ).json()

    assert ids(client.get("/api/admin/parents", headers=auth(coach))) == [created["id"]]
    assert ids(client.get("/api/admin/parents", headers=auth(other_coach))) == []


def test_coach_cannot_link_another_coachs_student(client, coach, others_student):
    response = client.post(
        "/api/admin/parents",
        json={"full_name": "Veli", "email": "v@test.dev", "password": "gizli-sifre", "student_ids": [others_student.id]},
        headers=auth(coach),
    )
    assert response.status_code == 422


def test_shared_parent_keeps_links_coach_cannot_see(client, admin, coach, own_student, others_student):
    """A parent with children at two coaches: each coach sees and edits only their own child."""
    parent = client.post(
        "/api/admin/parents",
        json={
            "full_name": "Veli",
            "email": "v@test.dev",
            "password": "gizli-sifre",
            "student_ids": [own_student.id, others_student.id],
        },
        headers=admin,
    ).json()

    seen = client.get("/api/admin/parents", headers=auth(coach)).json()[0]
    assert [s["id"] for s in seen["students"]] == [own_student.id]

    response = client.patch(f"/api/admin/parents/{parent['id']}", json={"student_ids": []}, headers=auth(coach))
    assert response.json()["students"] == []
    full = client.get("/api/admin/parents", headers=admin).json()[0]
    assert [s["id"] for s in full["students"]] == [others_student.id]
