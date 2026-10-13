import pytest

from app.models import Role
from tests.conftest import auth, make_user

EXAM = {"name": "Deneme 1", "exam_date": "2026-10-10", "publisher": "Özdebir"}


@pytest.fixture
def subjects(client, admin):
    return client.get("/api/admin/subjects", headers=admin).json()


@pytest.fixture
def exam_id(client, admin):
    return client.post("/api/admin/exams", json=EXAM, headers=admin).json()["id"]


def full_results(subjects, wrong=3, blank=1):
    """A valid entry for every subject."""
    return [
        {
            "subject_id": s["id"],
            "correct": s["question_count"] - wrong - blank,
            "wrong": wrong,
            "blank": blank,
            "mistake_topic_ids": [],
        }
        for s in subjects
    ]


def save(client, admin, exam_id, student_id, results):
    return client.put(
        f"/api/admin/exams/{exam_id}/students/{student_id}/results", json={"results": results}, headers=admin
    )


def test_subjects_are_seeded_for_lgs(subjects):
    assert [(s["code"], s["question_count"]) for s in subjects] == [
        ("turkce", 20),
        ("inkilap", 10),
        ("din", 10),
        ("ingilizce", 10),
        ("matematik", 20),
        ("fen", 20),
    ]
    assert all(s["topics"] for s in subjects)


def test_only_admin_can_use_exam_endpoints(client, student, exam_id, subjects):
    headers = auth(student)

    assert client.get("/api/admin/exams").status_code == 401
    assert client.get("/api/admin/exams", headers=headers).status_code == 403
    assert client.post("/api/admin/exams", json=EXAM, headers=headers).status_code == 403
    assert save(client, headers, exam_id, student.id, full_results(subjects)).status_code == 403


def test_create_and_list_exams(client, admin):
    created = client.post("/api/admin/exams", json={**EXAM, "name": "  Deneme 1 ", "publisher": "  "}, headers=admin)
    later = client.post("/api/admin/exams", json={"name": "Deneme 2", "exam_date": "2026-11-01"}, headers=admin)

    assert created.status_code == 201
    assert created.json() == {
        "id": created.json()["id"],
        "name": "Deneme 1",
        "exam_date": "2026-10-10",
        "publisher": None,
        "student_count": 0,
    }
    # Newest exam first.
    assert [e["name"] for e in client.get("/api/admin/exams", headers=admin).json()] == ["Deneme 2", "Deneme 1"]
    assert later.json()["publisher"] is None


def test_create_exam_validates_input(client, admin):
    for bad in ({"name": "   "}, {"exam_date": "10.10.2026"}):
        assert client.post("/api/admin/exams", json={**EXAM, **bad}, headers=admin).status_code == 422, bad


def test_save_results_computes_net(client, admin, exam_id, student, subjects):
    results = full_results(subjects)
    results[0].update(correct=10, wrong=4, blank=6)  # Türkçe: 10 - 4/3 = 8.67

    response = save(client, admin, exam_id, student.id, results)

    assert response.status_code == 200
    body = response.json()
    assert body["full_name"] == "Ayşe Demir"
    assert [r["net"] for r in body["results"]] == [8.67, 5.0, 5.0, 5.0, 15.0, 15.0]
    assert body["total_net"] == 53.67
    # Results come back in booklet order.
    assert [r["subject_id"] for r in body["results"]] == [s["id"] for s in subjects]


def test_total_net_is_not_a_sum_of_rounded_nets(client, admin, exam_id, student, subjects):
    # 5 correct, 1 wrong in every subject: 6 x 4.67 would give 28.02, the real total is 30 - 6/3.
    results = [
        {"subject_id": s["id"], "correct": 5, "wrong": 1, "blank": s["question_count"] - 6} for s in subjects
    ]

    body = save(client, admin, exam_id, student.id, results).json()

    assert [r["net"] for r in body["results"]] == [4.67] * 6
    assert body["total_net"] == 28.0


@pytest.mark.parametrize(("correct", "wrong", "blank"), [(15, 3, 1), (15, 3, 3), (21, 0, 0)])
def test_save_results_rejects_wrong_question_total(client, admin, exam_id, student, subjects, correct, wrong, blank):
    results = full_results(subjects)
    results[4].update(correct=correct, wrong=wrong, blank=blank)

    response = save(client, admin, exam_id, student.id, results)

    assert response.status_code == 422
    assert response.json()["detail"] == "Matematik: doğru + yanlış + boş toplamı 20 olmalıdır"
    # Nothing is saved when any subject is invalid.
    assert client.get(f"/api/admin/exams/{exam_id}", headers=admin).json()["students"] == []


def test_save_results_rejects_negative_numbers(client, admin, exam_id, student, subjects):
    results = full_results(subjects)
    results[0].update(correct=21, wrong=-1, blank=0)

    assert save(client, admin, exam_id, student.id, results).status_code == 422


def test_save_results_requires_every_subject_once(client, admin, exam_id, student, subjects):
    results = full_results(subjects)

    missing = save(client, admin, exam_id, student.id, results[:-1])
    duplicated = save(client, admin, exam_id, student.id, results[:-1] + [results[0]])

    assert missing.status_code == duplicated.status_code == 422
    assert missing.json()["detail"] == "Tüm dersler için sonuç girilmelidir"


def test_save_results_with_topic_mistakes(client, admin, exam_id, student, subjects):
    results = full_results(subjects)
    topic_ids = [t["id"] for t in subjects[0]["topics"][:2]]
    results[0]["mistake_topic_ids"] = topic_ids

    body = save(client, admin, exam_id, student.id, results).json()

    assert sorted(body["results"][0]["mistake_topic_ids"]) == topic_ids
    assert body["results"][1]["mistake_topic_ids"] == []


def test_save_results_rejects_topic_of_another_subject(client, admin, exam_id, student, subjects):
    results = full_results(subjects)
    results[0]["mistake_topic_ids"] = [subjects[5]["topics"][0]["id"]]

    response = save(client, admin, exam_id, student.id, results)

    assert response.status_code == 422
    assert response.json()["detail"] == "Türkçe: seçilen konu bu derse ait değil"


def test_saving_again_replaces_earlier_results(client, admin, exam_id, student, subjects):
    first = full_results(subjects)
    first[0]["mistake_topic_ids"] = [subjects[0]["topics"][0]["id"]]
    save(client, admin, exam_id, student.id, first)

    save(client, admin, exam_id, student.id, full_results(subjects, wrong=0, blank=0))

    students = client.get(f"/api/admin/exams/{exam_id}", headers=admin).json()["students"]
    assert len(students) == 1
    assert students[0]["total_net"] == 90.0
    assert students[0]["results"][0]["mistake_topic_ids"] == []


def test_results_are_only_for_existing_exams_and_students(client, admin, exam_id, student, subjects):
    parent = make_user(Role.parent, "veli@test.dev", "Veli")
    results = full_results(subjects)

    assert save(client, admin, 9999, student.id, results).status_code == 404
    assert save(client, admin, exam_id, 9999, results).status_code == 404
    assert save(client, admin, exam_id, parent.id, results).status_code == 404
    assert client.get("/api/admin/exams/9999", headers=admin).status_code == 404


def test_exam_detail_lists_students_by_name(client, admin, exam_id, student, subjects):
    other = make_user(Role.student, "ali@test.dev", "Ali Can")
    save(client, admin, exam_id, student.id, full_results(subjects))
    save(client, admin, exam_id, other.id, full_results(subjects, wrong=0))

    detail = client.get(f"/api/admin/exams/{exam_id}", headers=admin).json()

    assert detail["name"] == "Deneme 1"
    assert detail["student_count"] == 2
    assert [(s["full_name"], s["total_net"]) for s in detail["students"]] == [("Ali Can", 84.0), ("Ayşe Demir", 60.0)]
    assert client.get("/api/admin/exams", headers=admin).json()[0]["student_count"] == 2


def test_delete_student_results(client, admin, exam_id, student, subjects):
    other = make_user(Role.student, "ali@test.dev", "Ali Can")
    save(client, admin, exam_id, student.id, full_results(subjects))
    save(client, admin, exam_id, other.id, full_results(subjects))

    response = client.delete(f"/api/admin/exams/{exam_id}/students/{student.id}/results", headers=admin)

    assert response.status_code == 204
    students = client.get(f"/api/admin/exams/{exam_id}", headers=admin).json()["students"]
    assert [s["student_id"] for s in students] == [other.id]


def test_deactivated_student_keeps_exam_results(client, admin, exam_id, student, subjects):
    save(client, admin, exam_id, student.id, full_results(subjects))

    client.patch(f"/api/admin/students/{student.id}", json={"is_active": False}, headers=admin)

    students = client.get(f"/api/admin/exams/{exam_id}", headers=admin).json()["students"]
    assert [s["student_id"] for s in students] == [student.id]
