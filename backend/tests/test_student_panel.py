from datetime import date, timedelta

import pytest

from app.models import Role
from tests.conftest import auth, make_user

TODAY = date.today()


@pytest.fixture
def me(student):
    """Auth headers for the logged-in student."""
    return auth(student)


@pytest.fixture
def subjects(client, me):
    return client.get("/api/student/subjects", headers=me).json()


def log_payload(subjects, **overrides):
    turkce = subjects[0]
    return {
        "log_date": TODAY.isoformat(),
        "subject_id": turkce["id"],
        "topic_id": turkce["topics"][0]["id"],
        "solved": 40,
        "correct": 30,
        "wrong": 6,
        **overrides,
    }


def add_log(client, headers, subjects, **overrides):
    return client.post("/api/student/question-logs", json=log_payload(subjects, **overrides), headers=headers)


# --- access ---


def test_student_panel_is_only_for_students(client, admin, subjects):
    parent = auth(make_user(Role.parent, "veli@test.dev", "Veli"))

    for headers in ({}, admin, parent):
        expected = 403 if headers else 401
        assert client.get("/api/student/subjects", headers=headers).status_code == expected
        assert client.get("/api/student/question-logs", headers=headers).status_code == expected
        assert add_log(client, headers, subjects).status_code == expected
        assert client.get("/api/student/topic-progress", headers=headers).status_code == expected
        assert client.get("/api/student/analytics", headers=headers).status_code == expected


def test_admin_views_are_only_for_admin(client, student, me):
    assert client.get(f"/api/admin/students/{student.id}/question-logs", headers=me).status_code == 403
    assert client.get(f"/api/admin/students/{student.id}/topic-progress", headers=me).status_code == 403
    assert client.get(f"/api/admin/students/{student.id}/question-logs").status_code == 401


def test_student_gets_subjects_with_topics(subjects):
    assert [s["short_name"] for s in subjects] == ["Türkçe", "İnkılap", "Din", "İngilizce", "Mat", "Fen"]
    assert all(s["topics"] for s in subjects)


# --- daily question log ---


def test_add_and_list_question_logs(client, me, subjects):
    yesterday = (TODAY - timedelta(days=1)).isoformat()
    first = add_log(client, me, subjects, log_date=yesterday)
    second = add_log(client, me, subjects, subject_id=subjects[4]["id"], topic_id=None, solved=20, correct=20, wrong=0)
    third = add_log(client, me, subjects, solved=10, correct=4, wrong=6)

    assert first.status_code == second.status_code == third.status_code == 201
    assert first.json() == {
        "id": first.json()["id"],
        "log_date": yesterday,
        "subject_id": subjects[0]["id"],
        "topic_id": subjects[0]["topics"][0]["id"],
        "solved": 40,
        "correct": 30,
        "wrong": 6,
    }
    # A log without a topic is fine: mixed practice.
    assert second.json()["topic_id"] is None
    # Newest day first, and within a day the latest entry first.
    logs = client.get("/api/student/question-logs", headers=me).json()
    assert [log["id"] for log in logs] == [third.json()["id"], second.json()["id"], first.json()["id"]]


@pytest.mark.parametrize(
    "bad",
    [
        {"solved": 0, "correct": 0, "wrong": 0},
        {"solved": 10, "correct": 8, "wrong": 3},
        {"solved": 10, "correct": -1, "wrong": 0},
        {"solved": 1001, "correct": 0, "wrong": 0},
        {"subject_id": 9999, "topic_id": None},
        {"topic_id": 999999},
        {"log_date": "not-a-date"},
        {"log_date": (TODAY + timedelta(days=3)).isoformat()},
    ],
)
def test_add_question_log_validates_input(client, me, subjects, bad):
    assert add_log(client, me, subjects, **bad).status_code == 422
    assert client.get("/api/student/question-logs", headers=me).json() == []


def test_add_question_log_rejects_topic_of_another_subject(client, me, subjects):
    response = add_log(client, me, subjects, topic_id=subjects[4]["topics"][0]["id"])

    assert response.status_code == 422
    assert response.json()["detail"] == "Seçilen konu bu derse ait değil"


def test_question_logs_cover_the_requested_days(client, me, subjects):
    for days_ago in (0, 6, 7, 40):
        add_log(client, me, subjects, log_date=(TODAY - timedelta(days=days_ago)).isoformat())

    def count(query=""):
        return len(client.get(f"/api/student/question-logs{query}", headers=me).json())

    assert count() == 3  # default: last 30 days
    assert count("?days=7") == 2  # today and the six days before it
    assert count("?days=1") == 1
    assert count("?days=365") == 4
    assert client.get("/api/student/question-logs?days=0", headers=me).status_code == 422


def test_students_only_see_and_delete_their_own_logs(client, me, subjects):
    other = auth(make_user(Role.student, "ali@test.dev", "Ali Can"))
    mine = add_log(client, me, subjects).json()
    theirs = add_log(client, other, subjects).json()

    assert [log["id"] for log in client.get("/api/student/question-logs", headers=me).json()] == [mine["id"]]
    assert client.delete(f"/api/student/question-logs/{theirs['id']}", headers=me).status_code == 404
    assert client.delete("/api/student/question-logs/999999", headers=me).status_code == 404
    assert [log["id"] for log in client.get("/api/student/question-logs", headers=other).json()] == [theirs["id"]]


def test_delete_question_log(client, me, subjects):
    keep = add_log(client, me, subjects).json()
    remove = add_log(client, me, subjects).json()

    assert client.delete(f"/api/student/question-logs/{remove['id']}", headers=me).status_code == 204
    assert [log["id"] for log in client.get("/api/student/question-logs", headers=me).json()] == [keep["id"]]


def test_admin_sees_a_students_question_logs(client, admin, student, me, subjects):
    other = make_user(Role.student, "ali@test.dev", "Ali Can")
    mine = add_log(client, me, subjects).json()
    add_log(client, me, subjects, log_date=(TODAY - timedelta(days=40)).isoformat())
    add_log(client, auth(other), subjects)

    logs = client.get(f"/api/admin/students/{student.id}/question-logs", headers=admin)
    older = client.get(f"/api/admin/students/{student.id}/question-logs?days=60", headers=admin)

    assert logs.status_code == 200
    assert logs.json() == [mine]
    assert len(older.json()) == 2
    assert client.get("/api/admin/students/9999/question-logs", headers=admin).status_code == 404
    # Admin cannot write through the student endpoints.
    assert add_log(client, admin, subjects).status_code == 403


# --- topic progress ---


def test_topic_progress_starts_empty_and_can_be_set_and_changed(client, me, subjects):
    first, second = (t["id"] for t in subjects[0]["topics"][:2])
    assert client.get("/api/student/topic-progress", headers=me).json() == []

    created = client.put(f"/api/student/topic-progress/{first}", json={"status": "studying"}, headers=me)
    client.put(f"/api/student/topic-progress/{second}", json={"status": "done"}, headers=me)
    changed = client.put(f"/api/student/topic-progress/{first}", json={"status": "needs_review"}, headers=me)

    assert created.status_code == changed.status_code == 200
    assert created.json() == {"topic_id": first, "status": "studying"}
    progress = client.get("/api/student/topic-progress", headers=me).json()
    assert sorted(progress, key=lambda p: p["topic_id"]) == [
        {"topic_id": first, "status": "needs_review"},
        {"topic_id": second, "status": "done"},
    ]


def test_topic_can_be_set_back_to_not_started(client, me, subjects):
    topic_id = subjects[0]["topics"][0]["id"]
    client.put(f"/api/student/topic-progress/{topic_id}", json={"status": "done"}, headers=me)

    response = client.put(f"/api/student/topic-progress/{topic_id}", json={"status": "not_started"}, headers=me)

    assert response.json() == {"topic_id": topic_id, "status": "not_started"}


def test_topic_progress_validates_input(client, me, subjects):
    topic_id = subjects[0]["topics"][0]["id"]

    assert client.put(f"/api/student/topic-progress/{topic_id}", json={"status": "mastered"}, headers=me).status_code == 422
    assert client.put("/api/student/topic-progress/999999", json={"status": "done"}, headers=me).status_code == 404


def test_topic_progress_is_per_student_and_visible_to_admin(client, admin, student, me, subjects):
    other = make_user(Role.student, "ali@test.dev", "Ali Can")
    topic_id = subjects[0]["topics"][0]["id"]
    client.put(f"/api/student/topic-progress/{topic_id}", json={"status": "done"}, headers=me)
    client.put(f"/api/student/topic-progress/{topic_id}", json={"status": "studying"}, headers=auth(other))

    assert client.get("/api/student/topic-progress", headers=me).json() == [{"topic_id": topic_id, "status": "done"}]
    for student_id, expected in ((student.id, "done"), (other.id, "studying")):
        response = client.get(f"/api/admin/students/{student_id}/topic-progress", headers=admin)
        assert response.json() == [{"topic_id": topic_id, "status": expected}]
    assert client.get("/api/admin/students/9999/topic-progress", headers=admin).status_code == 404


# --- own exam analytics ---


def test_student_sees_the_same_analytics_as_admin(client, admin, student, me, subjects):
    other = make_user(Role.student, "ali@test.dev", "Ali Can")
    for exam_date, corrects in (("2026-09-01", [10, 5, 5, 5, 10, 10]), ("2026-10-01", [14, 6, 5, 7, 12, 9])):
        exam_id = client.post("/api/admin/exams", json={"name": "Deneme", "exam_date": exam_date}, headers=admin).json()["id"]
        for who, bonus in ((student, 0), (other, 2)):
            results = [
                {
                    "subject_id": s["id"],
                    "correct": correct + bonus,
                    "wrong": 1,
                    "blank": s["question_count"] - correct - bonus - 1,
                    "mistake_topic_ids": [s["topics"][0]["id"]],
                }
                for s, correct in zip(subjects, corrects)
            ]
            client.put(f"/api/admin/exams/{exam_id}/students/{who.id}/results", json={"results": results}, headers=admin)

    mine = client.get("/api/student/analytics", headers=me)

    assert mine.status_code == 200
    assert mine.json() == client.get(f"/api/admin/students/{student.id}/analytics", headers=admin).json()
    assert mine.json()["student"]["id"] == student.id
    assert len(mine.json()["exams"]) == 2
    # The other student gets their own numbers, not ours.
    theirs = client.get("/api/student/analytics", headers=auth(other)).json()
    assert theirs["student"]["id"] == other.id
    assert theirs["exams"][0]["total_net"] != mine.json()["exams"][0]["total_net"]


def test_student_analytics_without_exams(client, me):
    body = client.get("/api/student/analytics", headers=me).json()

    assert body["exams"] == [] and body["comparison"] is None
