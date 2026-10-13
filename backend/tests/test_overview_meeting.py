from datetime import date, timedelta

import pytest

from app.database import SessionLocal
from app.models import MeetingNote, Role, User
from tests.conftest import auth, make_user
from tests.test_analytics import enter, subjects  # noqa: F401 (fixtures)
from tests.test_parent_panel import add_log, add_note

TODAY = date.today()


def days_ago(days):
    return (TODAY - timedelta(days=days)).isoformat()


def overview(client, admin):
    response = client.get("/api/admin/overview", headers=admin)
    assert response.status_code == 200
    return response.json()


def meeting(client, admin, student):
    response = client.get(f"/api/admin/students/{student.id}/meeting", headers=admin)
    assert response.status_code == 200
    return response.json()


def add_meeting_note(client, admin, student, meeting_date, body="Çalışma programı konuşuldu."):
    return client.post(
        f"/api/admin/students/{student.id}/meeting-notes",
        json={"meeting_date": meeting_date, "body": body},
        headers=admin,
    )


def set_status(client, student, topic, status):
    response = client.put(f"/api/student/topic-progress/{topic['id']}", json={"status": status}, headers=auth(student))
    assert response.status_code == 200


# --- admin overview ---


def test_overview_is_only_for_admin(client, student):
    parent = make_user(Role.parent, "veli@test.dev", "Veli")

    assert client.get("/api/admin/overview").status_code == 401
    assert client.get("/api/admin/overview", headers=auth(student)).status_code == 403
    assert client.get("/api/admin/overview", headers=auth(parent)).status_code == 403


def test_overview_lists_active_students_by_name(client, admin, student):
    make_user(Role.student, "zeynep@test.dev", "Zeynep Ak", class_name="8-B")
    make_user(Role.student, "ali@test.dev", "Ali Kaya")
    make_user(Role.student, "pasif@test.dev", "Pasif Öğrenci", is_active=False)
    make_user(Role.parent, "veli@test.dev", "Veli")

    rows = overview(client, admin)

    assert [r["full_name"] for r in rows] == ["Ali Kaya", "Ayşe Demir", "Zeynep Ak"]
    assert rows[2]["class_name"] == "8-B"


def test_overview_row_for_a_student_without_any_data(client, admin, student):
    assert overview(client, admin) == [
        {
            "student_id": student.id,
            "full_name": "Ayşe Demir",
            "class_name": None,
            "last_exam": None,
            "week_solved": 0,
            "weak_topic_count": 0,
            "last_log_date": None,
            "no_recent_log": True,
        }
    ]


def test_overview_shows_last_exam_net_and_change_from_previous(client, admin, student, enter):
    enter(student, "2026-03-01", [10, 5, 5, 5, 10, 10], name="Mart")
    enter(student, "2026-01-01", [20, 10, 10, 10, 20, 20], name="Ocak")
    last = enter(student, "2026-04-01", [12, 6, 6, 6, 9, 10], name="Nisan")

    assert overview(client, admin)[0]["last_exam"] == {
        "exam_id": last,
        "name": "Nisan",
        "exam_date": "2026-04-01",
        "total_net": 49.0,
        "change": 4.0,
    }


def test_overview_has_no_change_for_a_first_exam(client, admin, student, enter):
    enter(student, "2026-03-01", [10, 5, 5, 5, 10, 10])

    last_exam = overview(client, admin)[0]["last_exam"]

    assert last_exam["total_net"] == 45.0
    assert last_exam["change"] is None


def test_overview_net_matches_the_analytics_page(client, admin, student, subjects):
    """Three subjects with 1 wrong each: 3 × 0.33 would add up to 0.99, the real total is 1 net lost."""
    exam_id = client.post("/api/admin/exams", json={"name": "D", "exam_date": "2026-03-01"}, headers=admin).json()["id"]
    results = [
        {"subject_id": s["id"], "correct": 5, "wrong": 1 if i < 3 else 0, "blank": s["question_count"] - 5 - (i < 3)}
        for i, s in enumerate(subjects)
    ]
    client.put(f"/api/admin/exams/{exam_id}/students/{student.id}/results", json={"results": results}, headers=admin)

    total = client.get(f"/api/admin/students/{student.id}/analytics", headers=admin).json()["comparison"]["total"]["last"]

    assert overview(client, admin)[0]["last_exam"]["total_net"] == total == 29.0


def test_overview_keeps_each_students_exams_apart(client, admin, student, enter):
    other = make_user(Role.student, "zeynep@test.dev", "Zeynep Ak")
    first = enter(student, "2026-03-01", [10, 5, 5, 5, 10, 10])
    enter(other, "2026-03-01", [20, 10, 10, 10, 20, 20], exam_id=first)
    enter(student, "2026-04-01", [10, 5, 5, 5, 10, 15])

    ayse, zeynep = overview(client, admin)

    assert (ayse["last_exam"]["total_net"], ayse["last_exam"]["change"]) == (50.0, 5.0)
    assert (zeynep["last_exam"]["total_net"], zeynep["last_exam"]["change"]) == (90.0, None)


def test_overview_counts_questions_of_the_last_7_days(client, admin, student, subjects):
    add_log(client, student, subjects, 0, 20, 15, 5)
    add_log(client, student, subjects, 6, 30, 20, 5, subject=4)
    add_log(client, student, subjects, 7, 100, 50, 50)

    row = overview(client, admin)[0]

    assert row["week_solved"] == 50
    assert row["last_log_date"] == days_ago(0)


def test_overview_counts_topics_missed_in_at_least_2_of_the_last_3_exams(client, admin, student, enter):
    other = make_user(Role.student, "zeynep@test.dev", "Zeynep Ak")
    # An old exam outside the last 3: its Science topic does not count.
    enter(student, "2026-01-01", [10, 5, 5, 5, 10, 10], wrong_topics={5: 1})
    first = enter(student, "2026-03-01", [10, 5, 5, 5, 10, 10], wrong_topics={0: 2, 4: 1})
    enter(student, "2026-04-01", [10, 5, 5, 5, 10, 10], wrong_topics={0: 3, 5: 1})
    enter(student, "2026-05-01", [10, 5, 5, 5, 10, 10], wrong_topics={0: 1})
    # Missed in a single exam only.
    enter(other, "2026-03-01", [10, 5, 5, 5, 10, 10], exam_id=first, wrong_topics={5: 1})

    ayse, zeynep = overview(client, admin)

    # The first two Turkish topics repeat; the third, Math and Science were each missed once.
    assert ayse["weak_topic_count"] == 2
    assert zeynep["weak_topic_count"] == 0
    analytics = client.get(f"/api/admin/students/{student.id}/analytics", headers=admin).json()
    assert len(analytics["weak_topics"]) == ayse["weak_topic_count"]


@pytest.mark.parametrize("last_log_days_ago, warned", [(0, False), (2, False), (3, True), (10, True)])
def test_overview_warns_when_there_is_no_log_in_the_last_3_days(
    client, admin, student, subjects, last_log_days_ago, warned
):
    add_log(client, student, subjects, last_log_days_ago, 20, 15, 5)
    add_log(client, student, subjects, 20, 20, 15, 5)

    row = overview(client, admin)[0]

    assert row["no_recent_log"] is warned
    assert row["last_log_date"] == days_ago(last_log_days_ago)


# --- parent meeting page ---


def test_meeting_page_is_only_for_admin(client, admin, student):
    parent = make_user(Role.parent, "veli@test.dev", "Veli")
    url = f"/api/admin/students/{student.id}/meeting"

    assert client.get(url).status_code == 401
    assert client.get(url, headers=auth(student)).status_code == 403
    assert client.get(url, headers=auth(parent)).status_code == 403
    assert client.get("/api/admin/students/999/meeting", headers=admin).status_code == 404
    assert client.get(f"/api/admin/students/{parent.id}/meeting", headers=admin).status_code == 404


def test_meeting_page_for_a_student_without_any_data(client, admin, student, subjects):
    page = meeting(client, admin, student)

    assert page["analytics"]["student"]["full_name"] == "Ayşe Demir"
    assert page["analytics"]["exams"] == []
    assert page["questions"]["solved"] == 0
    assert len(page["questions"]["days"]) == 30
    assert page["questions_by_subject"] == []
    assert [p["subject_id"] for p in page["topic_progress"]] == [s["id"] for s in subjects]
    assert all(p["not_started"] == p["total"] == len(s["topics"]) for p, s in zip(page["topic_progress"], subjects))
    assert page["notes"] == []
    assert page["meeting_notes"] == []


def test_meeting_page_includes_the_exam_analytics(client, admin, student, enter):
    enter(student, "2026-03-01", [10, 5, 5, 5, 10, 10], wrong_topics={4: 2})
    enter(student, "2026-04-01", [12, 6, 6, 6, 10, 10], wrong_topics={4: 3})

    analytics = meeting(client, admin, student)["analytics"]

    assert analytics == client.get(f"/api/admin/students/{student.id}/analytics", headers=admin).json()
    assert analytics["comparison"]["total"]["change"] == 5.0
    assert len(analytics["weak_topics"]) == 2


def test_meeting_page_sums_questions_of_the_last_30_days(client, admin, student, subjects):
    add_log(client, student, subjects, 0, 20, 15, 5)
    add_log(client, student, subjects, 0, 10, 5, 2, subject=4)
    add_log(client, student, subjects, 29, 30, 20, 5, subject=4)
    add_log(client, student, subjects, 30, 100, 50, 50)

    page = meeting(client, admin, student)

    questions = page["questions"]
    assert (questions["solved"], questions["correct"], questions["wrong"]) == (60, 40, 12)
    assert questions["active_days"] == 2
    assert questions["days"][0] == {"day": days_ago(29), "solved": 30, "correct": 20, "wrong": 5}
    assert questions["days"][-1] == {"day": days_ago(0), "solved": 30, "correct": 20, "wrong": 7}
    assert page["questions_by_subject"] == [
        {"subject_id": subjects[0]["id"], "solved": 20, "correct": 15, "wrong": 5},
        {"subject_id": subjects[4]["id"], "solved": 40, "correct": 25, "wrong": 7},
    ]


def test_meeting_page_counts_topic_progress_per_subject(client, admin, student, subjects):
    other = make_user(Role.student, "zeynep@test.dev", "Zeynep Ak")
    turkish, math = subjects[0], subjects[4]
    set_status(client, student, turkish["topics"][0], "done")
    set_status(client, student, turkish["topics"][1], "done")
    set_status(client, student, turkish["topics"][2], "studying")
    set_status(client, student, turkish["topics"][3], "not_started")
    set_status(client, student, math["topics"][0], "needs_review")
    set_status(client, other, math["topics"][1], "done")

    progress = meeting(client, admin, student)["topic_progress"]

    total = len(turkish["topics"])
    assert progress[0] == {
        "subject_id": turkish["id"],
        "total": total,
        "not_started": total - 3,
        "studying": 1,
        "done": 2,
        "needs_review": 0,
    }
    assert (progress[4]["needs_review"], progress[4]["done"]) == (1, 0)
    assert all(p["not_started"] + p["studying"] + p["done"] + p["needs_review"] == p["total"] for p in progress)


def test_meeting_page_shows_only_coach_notes_visible_to_the_parent(client, admin, student):
    add_note(client, admin, student, body="Veliye açık not")
    add_note(client, admin, student, body="Sadece koç için", visible=False)

    assert [n["body"] for n in meeting(client, admin, student)["notes"]] == ["Veliye açık not"]


# --- meeting notes ---


def test_admin_adds_a_meeting_note_with_its_date(client, admin, student):
    response = add_meeting_note(client, admin, student, days_ago(1), body="  Hedef net 70 olarak belirlendi.  ")

    assert response.status_code == 201
    assert response.json()["meeting_date"] == days_ago(1)
    assert response.json()["body"] == "Hedef net 70 olarak belirlendi."
    assert meeting(client, admin, student)["meeting_notes"] == [response.json()]


def test_meeting_notes_are_listed_latest_meeting_first_per_student(client, admin, student):
    other = make_user(Role.student, "zeynep@test.dev", "Zeynep Ak")
    add_meeting_note(client, admin, student, days_ago(30), body="Eski")
    add_meeting_note(client, admin, student, days_ago(0), body="Bugün")
    add_meeting_note(client, admin, student, days_ago(7), body="Geçen hafta")
    add_meeting_note(client, admin, other, days_ago(1), body="Başka öğrenci")

    assert [n["body"] for n in meeting(client, admin, student)["meeting_notes"]] == ["Bugün", "Geçen hafta", "Eski"]
    assert [n["body"] for n in meeting(client, admin, other)["meeting_notes"]] == ["Başka öğrenci"]


@pytest.mark.parametrize(
    "payload",
    [
        {"meeting_date": days_ago(0), "body": "   "},
        {"meeting_date": days_ago(-1), "body": "Yarınki görüşme"},
        {"meeting_date": "dün", "body": "Not"},
        {"body": "Tarihsiz"},
        {"meeting_date": days_ago(0), "body": "x" * 4001},
    ],
)
def test_invalid_meeting_notes_are_rejected(client, admin, student, payload):
    response = client.post(f"/api/admin/students/{student.id}/meeting-notes", json=payload, headers=admin)

    assert response.status_code == 422
    assert meeting(client, admin, student)["meeting_notes"] == []


def test_meeting_note_needs_an_existing_student(client, admin):
    parent = make_user(Role.parent, "veli@test.dev", "Veli")

    assert client.post(
        "/api/admin/students/999/meeting-notes", json={"meeting_date": days_ago(0), "body": "Not"}, headers=admin
    ).status_code == 404
    assert add_meeting_note(client, admin, parent, days_ago(0)).status_code == 404


def test_admin_deletes_a_meeting_note(client, admin, student):
    note = add_meeting_note(client, admin, student, days_ago(0)).json()

    assert client.delete(f"/api/admin/meeting-notes/{note['id']}", headers=admin).status_code == 204
    assert meeting(client, admin, student)["meeting_notes"] == []
    assert client.delete(f"/api/admin/meeting-notes/{note['id']}", headers=admin).status_code == 404


def test_only_admin_can_write_meeting_notes(client, admin, student):
    parent = make_user(Role.parent, "veli@test.dev", "Veli")
    note = add_meeting_note(client, admin, student, days_ago(0)).json()

    for headers in (auth(student), auth(parent)):
        assert add_meeting_note(client, headers, student, days_ago(0)).status_code == 403
        assert client.delete(f"/api/admin/meeting-notes/{note['id']}", headers=headers).status_code == 403
    assert len(meeting(client, admin, student)["meeting_notes"]) == 1


def test_meeting_notes_are_deleted_with_the_student(client, admin, student):
    add_meeting_note(client, admin, student, days_ago(0))
    with SessionLocal() as db:
        db.delete(db.get(User, student.id))
        db.commit()
        assert db.query(MeetingNote).count() == 0
