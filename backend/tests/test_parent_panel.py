from datetime import date, timedelta

import pytest

from app.database import SessionLocal
from app.models import Role, User
from tests.conftest import auth, make_user

TODAY = date.today()


def link(parent, *students):
    with SessionLocal() as db:
        db.get(User, parent.id).students = [db.get(User, s.id) for s in students]
        db.commit()


@pytest.fixture
def parent(student):
    """A parent linked to the `student` fixture."""
    parent = make_user(Role.parent, "veli@test.dev", "Fatma Demir")
    link(parent, student)
    return parent


@pytest.fixture
def subjects(client, admin):
    return client.get("/api/admin/subjects", headers=admin).json()


def children(client, parent):
    response = client.get("/api/parent/children", headers=auth(parent))
    assert response.status_code == 200
    return response.json()


def add_log(client, student, subjects, days_ago, solved, correct, wrong, subject=0):
    payload = {
        "log_date": (TODAY - timedelta(days=days_ago)).isoformat(),
        "subject_id": subjects[subject]["id"],
        "topic_id": None,
        "solved": solved,
        "correct": correct,
        "wrong": wrong,
    }
    assert client.post("/api/student/question-logs", json=payload, headers=auth(student)).status_code == 201


def add_note(client, admin, student, body="Düzenli çalışıyor.", visible=True):
    response = client.post(
        f"/api/admin/students/{student.id}/notes", json={"body": body, "visible_to_parent": visible}, headers=admin
    )
    assert response.status_code == 201
    return response.json()


# --- parent panel ---


def test_parent_panel_is_only_for_parents(client, admin, student):
    assert client.get("/api/parent/children").status_code == 401
    assert client.get("/api/parent/children", headers=admin).status_code == 403
    assert client.get("/api/parent/children", headers=auth(student)).status_code == 403


def test_parent_sees_only_linked_children(client, parent, student):
    make_user(Role.student, "baska@test.dev", "Başka Öğrenci")
    sibling = make_user(Role.student, "kardes@test.dev", "Can Demir")
    assert [c["analytics"]["student"]["full_name"] for c in children(client, parent)] == ["Ayşe Demir"]

    link(parent, student, sibling)

    assert [c["analytics"]["student"]["full_name"] for c in children(client, parent)] == ["Ayşe Demir", "Can Demir"]


def test_parent_without_children_gets_an_empty_list(client):
    lonely = make_user(Role.parent, "veli2@test.dev", "Veli")

    assert children(client, lonely) == []


def test_deactivated_child_is_hidden(client, admin, parent, student):
    client.patch(f"/api/admin/students/{student.id}", json={"is_active": False}, headers=admin)

    assert children(client, parent) == []


def test_child_without_data(client, parent):
    [child] = children(client, parent)

    assert child["analytics"]["exams"] == []
    assert child["analytics"]["comparison"] is None
    assert child["notes"] == []
    assert child["week"]["solved"] == child["week"]["active_days"] == 0
    assert [d["solved"] for d in child["week"]["days"]] == [0] * 7


def test_child_summary_has_the_childs_exam_analytics(client, admin, parent, student, subjects):
    for exam_date, correct in (("2026-09-01", 5), ("2026-10-01", 7)):
        exam_id = client.post("/api/admin/exams", json={"name": "Deneme", "exam_date": exam_date}, headers=admin).json()["id"]
        results = [
            {
                "subject_id": s["id"],
                "correct": correct,
                "wrong": 0,
                "blank": s["question_count"] - correct,
                "mistake_topic_ids": [s["topics"][0]["id"]],
            }
            for s in subjects
        ]
        client.put(f"/api/admin/exams/{exam_id}/students/{student.id}/results", json={"results": results}, headers=admin)

    [child] = children(client, parent)

    assert child["analytics"] == client.get(f"/api/admin/students/{student.id}/analytics", headers=admin).json()
    assert [e["total_net"] for e in child["analytics"]["exams"]] == [30.0, 42.0]
    assert child["analytics"]["comparison"]["total"]["change"] == 12.0
    assert child["analytics"]["weak_topics"][0]["count"] == 2


def test_week_covers_the_last_seven_days(client, parent, student, subjects):
    other = make_user(Role.student, "ali@test.dev", "Ali Can")
    add_log(client, student, subjects, days_ago=0, solved=40, correct=30, wrong=6)
    add_log(client, student, subjects, days_ago=0, solved=10, correct=10, wrong=0, subject=4)
    add_log(client, student, subjects, days_ago=6, solved=20, correct=12, wrong=8)
    add_log(client, student, subjects, days_ago=7, solved=99, correct=0, wrong=0)  # too old
    add_log(client, other, subjects, days_ago=1, solved=50, correct=50, wrong=0)  # someone else's

    week = children(client, parent)[0]["week"]

    assert (week["solved"], week["correct"], week["wrong"], week["active_days"]) == (70, 52, 14, 2)
    # Oldest day first, today last, quiet days as zero.
    assert [d["day"] for d in week["days"]] == [(TODAY - timedelta(days=n)).isoformat() for n in range(6, -1, -1)]
    assert [d["solved"] for d in week["days"]] == [20, 0, 0, 0, 0, 0, 50]
    assert week["days"][-1] == {"day": TODAY.isoformat(), "solved": 50, "correct": 40, "wrong": 6}


def test_parent_sees_only_visible_notes_for_their_child(client, admin, parent, student):
    other = make_user(Role.student, "ali@test.dev", "Ali Can")
    first = add_note(client, admin, student, "İlk not.")
    add_note(client, admin, student, "Sadece koç için.", visible=False)
    second = add_note(client, admin, student, "İkinci not.")
    add_note(client, admin, other, "Başka öğrencinin notu.")

    notes = children(client, parent)[0]["notes"]

    # Newest first; no visibility flag is exposed to the parent.
    assert [(n["id"], n["body"]) for n in notes] == [(second["id"], "İkinci not."), (first["id"], "İlk not.")]
    assert set(notes[0]) == {"id", "body", "created_at"}


def test_hiding_a_note_removes_it_from_the_parent_view(client, admin, parent, student):
    note = add_note(client, admin, student)
    assert len(children(client, parent)[0]["notes"]) == 1

    client.patch(f"/api/admin/notes/{note['id']}", json={"visible_to_parent": False}, headers=admin)

    assert children(client, parent)[0]["notes"] == []


# --- coach notes (admin) ---


def test_only_admin_can_manage_notes(client, parent, student):
    for who in (parent, student):
        headers = auth(who)
        assert client.get(f"/api/admin/students/{student.id}/notes", headers=headers).status_code == 403
        assert client.post(f"/api/admin/students/{student.id}/notes", json={"body": "x"}, headers=headers).status_code == 403
    assert client.get(f"/api/admin/students/{student.id}/notes").status_code == 401


def test_add_and_list_notes(client, admin, student):
    hidden = client.post(f"/api/admin/students/{student.id}/notes", json={"body": "  Süre yönetimi.  "}, headers=admin)
    visible = add_note(client, admin, student, "Veliye not.")

    assert hidden.status_code == 201
    # Notes are private unless the admin says otherwise.
    assert (hidden.json()["body"], hidden.json()["visible_to_parent"]) == ("Süre yönetimi.", False)
    notes = client.get(f"/api/admin/students/{student.id}/notes", headers=admin).json()
    assert [(n["id"], n["visible_to_parent"]) for n in notes] == [(visible["id"], True), (hidden.json()["id"], False)]


def test_notes_validate_input(client, admin, student):
    parent = make_user(Role.parent, "veli@test.dev", "Veli")

    assert client.post(f"/api/admin/students/{student.id}/notes", json={"body": "   "}, headers=admin).status_code == 422
    assert client.post(f"/api/admin/students/{student.id}/notes", json={"body": "x" * 2001}, headers=admin).status_code == 422
    # Notes are about students only.
    assert client.post(f"/api/admin/students/{parent.id}/notes", json={"body": "x"}, headers=admin).status_code == 404
    assert client.get("/api/admin/students/9999/notes", headers=admin).status_code == 404


def test_update_note(client, admin, student):
    note = add_note(client, admin, student, "Eski metin.", visible=False)

    shown = client.patch(f"/api/admin/notes/{note['id']}", json={"visible_to_parent": True}, headers=admin)
    edited = client.patch(f"/api/admin/notes/{note['id']}", json={"body": "Yeni metin."}, headers=admin)

    assert (shown.json()["body"], shown.json()["visible_to_parent"]) == ("Eski metin.", True)
    # Editing the text keeps the visibility.
    assert (edited.json()["body"], edited.json()["visible_to_parent"]) == ("Yeni metin.", True)
    assert client.patch(f"/api/admin/notes/{note['id']}", json={"body": ""}, headers=admin).status_code == 422
    assert client.patch("/api/admin/notes/9999", json={"body": "x"}, headers=admin).status_code == 404


def test_delete_note(client, admin, student):
    keep = add_note(client, admin, student, "Kalsın.")
    remove = add_note(client, admin, student, "Silinsin.")

    assert client.delete(f"/api/admin/notes/{remove['id']}", headers=admin).status_code == 204
    assert client.delete(f"/api/admin/notes/{remove['id']}", headers=admin).status_code == 404
    assert [n["id"] for n in client.get(f"/api/admin/students/{student.id}/notes", headers=admin).json()] == [keep["id"]]
