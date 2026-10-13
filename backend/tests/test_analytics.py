import pytest

from app.models import Role
from tests.conftest import auth, make_user


@pytest.fixture
def subjects(client, admin):
    return client.get("/api/admin/subjects", headers=admin).json()


@pytest.fixture
def enter(client, admin, subjects):
    """Create an exam and/or save results; returns the exam id.

    `corrects` lists the correct count per subject in booklet order; nothing is wrong, the
    rest is blank, so each subject's net equals its correct count. `wrong_topics` maps a
    subject index to how many of its first topics to mark as mistakes.
    """

    def _enter(student, exam_date, corrects, name="Deneme", exam_id=None, wrong_topics=None):
        if exam_id is None:
            exam_id = client.post(
                "/api/admin/exams", json={"name": name, "exam_date": exam_date}, headers=admin
            ).json()["id"]
        results = [
            {
                "subject_id": s["id"],
                "correct": correct,
                "wrong": 0,
                "blank": s["question_count"] - correct,
                "mistake_topic_ids": [t["id"] for t in s["topics"][: (wrong_topics or {}).get(i, 0)]],
            }
            for i, (s, correct) in enumerate(zip(subjects, corrects))
        ]
        response = client.put(
            f"/api/admin/exams/{exam_id}/students/{student.id}/results", json={"results": results}, headers=admin
        )
        assert response.status_code == 200
        return exam_id

    return _enter


def analytics(client, admin, student_id):
    return client.get(f"/api/admin/students/{student_id}/analytics", headers=admin)


def test_subjects_have_short_name_and_session(subjects):
    assert [(s["short_name"], s["session"]) for s in subjects] == [
        ("Türkçe", "sozel"),
        ("İnkılap", "sozel"),
        ("Din", "sozel"),
        ("İngilizce", "sozel"),
        ("Mat", "sayisal"),
        ("Fen", "sayisal"),
    ]


def test_only_admin_can_see_analytics(client, student):
    assert client.get(f"/api/admin/students/{student.id}/analytics").status_code == 401
    assert client.get(f"/api/admin/students/{student.id}/analytics", headers=auth(student)).status_code == 403


def test_analytics_is_only_for_students(client, admin):
    parent = make_user(Role.parent, "veli@test.dev", "Veli")

    assert analytics(client, admin, parent.id).status_code == 404
    assert analytics(client, admin, 9999).status_code == 404


def test_student_without_exams(client, admin, student, subjects):
    response = analytics(client, admin, student.id)

    assert response.status_code == 200
    body = response.json()
    assert body["student"]["full_name"] == "Ayşe Demir"
    assert [s["short_name"] for s in body["subjects"]] == [s["short_name"] for s in subjects]
    assert body["exams"] == []
    assert body["comparison"] is None
    assert body["weak_topics"] == []
    assert body["averages"] == []


def test_trend_lists_exams_oldest_first(client, admin, student, subjects, enter):
    # Entered out of order on purpose.
    enter(student, "2026-11-01", [15, 8, 8, 8, 15, 15], name="Kasım")
    enter(student, "2026-09-01", [10, 5, 5, 5, 10, 10], name="Eylül")
    enter(student, "2026-10-01", [12, 6, 6, 6, 12, 12], name="Ekim")

    exams = analytics(client, admin, student.id).json()["exams"]

    assert [(e["name"], e["exam_date"], e["total_net"]) for e in exams] == [
        ("Eylül", "2026-09-01", 45.0),
        ("Ekim", "2026-10-01", 54.0),
        ("Kasım", "2026-11-01", 69.0),
    ]
    assert exams[0]["nets"] == [
        {"subject_id": s["id"], "net": net} for s, net in zip(subjects, [10.0, 5.0, 5.0, 5.0, 10.0, 10.0])
    ]


def test_trend_only_includes_the_students_own_exams(client, admin, student, enter):
    other = make_user(Role.student, "ali@test.dev", "Ali Can")
    enter(student, "2026-09-01", [10, 5, 5, 5, 10, 10])
    enter(other, "2026-10-01", [20, 10, 10, 10, 20, 20])

    body = analytics(client, admin, student.id).json()

    assert [e["total_net"] for e in body["exams"]] == [45.0]


def test_comparison_of_last_two_exams(client, admin, student, subjects, enter):
    enter(student, "2026-09-01", [20, 10, 10, 10, 20, 20])  # older exams are ignored
    previous = enter(student, "2026-10-01", [12, 6, 6, 6, 12, 12])
    last = enter(student, "2026-11-01", [15, 4, 6, 8, 10, 12])

    comparison = analytics(client, admin, student.id).json()["comparison"]

    assert (comparison["last_exam_id"], comparison["previous_exam_id"]) == (last, previous)
    assert comparison["total"] == {"last": 55.0, "previous": 54.0, "change": 1.0}
    assert [(c["subject_id"], c["last"], c["previous"], c["change"]) for c in comparison["subjects"]] == [
        (s["id"], *values)
        for s, values in zip(
            subjects,
            [(15.0, 12.0, 3.0), (4.0, 6.0, -2.0), (6.0, 6.0, 0.0), (8.0, 6.0, 2.0), (10.0, 12.0, -2.0), (12.0, 12.0, 0.0)],
        )
    ]


def test_comparison_with_a_single_exam_has_no_previous(client, admin, student, enter):
    exam_id = enter(student, "2026-10-01", [12, 6, 6, 6, 12, 12])

    comparison = analytics(client, admin, student.id).json()["comparison"]

    assert (comparison["last_exam_id"], comparison["previous_exam_id"]) == (exam_id, None)
    assert comparison["total"] == {"last": 54.0, "previous": None, "change": None}
    assert all(c["previous"] is None and c["change"] is None for c in comparison["subjects"])


def test_comparison_does_not_accumulate_rounding(client, admin, student, subjects):
    def save(exam_date, wrong):
        exam_id = client.post("/api/admin/exams", json={"name": "D", "exam_date": exam_date}, headers=admin).json()["id"]
        results = [
            {"subject_id": s["id"], "correct": 5, "wrong": wrong, "blank": s["question_count"] - 5 - wrong}
            for s in subjects
        ]
        client.put(f"/api/admin/exams/{exam_id}/students/{student.id}/results", json={"results": results}, headers=admin)

    save("2026-10-01", wrong=1)  # net 4.67 per subject
    save("2026-11-01", wrong=2)  # net 4.33 per subject

    comparison = analytics(client, admin, student.id).json()["comparison"]

    # Change and totals come from the unrounded nets: -1/3, not 4.33 - 4.67 = -0.34.
    assert comparison["subjects"][0] | {"subject_id": 0} == {"subject_id": 0, "last": 4.33, "previous": 4.67, "change": -0.33}
    assert comparison["total"] == {"last": 26.0, "previous": 28.0, "change": -2.0}


def weak_topic_counts(client, admin, student):
    """Weak topics as (topic id, count) pairs."""
    return [(t["topic_id"], t["count"]) for t in analytics(client, admin, student.id).json()["weak_topics"]]


def test_weak_topics_are_those_missed_in_at_least_2_of_the_last_3_exams(client, admin, student, subjects, enter):
    other = make_user(Role.student, "ali@test.dev", "Ali Can")
    turkce, mat = subjects[0], subjects[4]
    exam_1 = enter(student, "2026-09-01", [10, 5, 5, 5, 10, 10], wrong_topics={0: 2, 4: 1})
    enter(student, "2026-10-01", [10, 5, 5, 5, 10, 10], wrong_topics={0: 1})
    enter(student, "2026-11-01", [10, 5, 5, 5, 10, 10], wrong_topics={0: 1, 4: 1})
    # Another student's mistakes do not count.
    enter(other, "2026-09-01", [10, 5, 5, 5, 10, 10], exam_id=exam_1, wrong_topics={5: 3})

    weak_topics = analytics(client, admin, student.id).json()["weak_topics"]

    # The second Turkish topic was missed only once, so it is not listed.
    assert weak_topics == [
        {"topic_id": turkce["topics"][0]["id"], "name": turkce["topics"][0]["name"], "subject_id": turkce["id"], "count": 3},
        {"topic_id": mat["topics"][0]["id"], "name": mat["topics"][0]["name"], "subject_id": mat["id"], "count": 2},
    ]
    assert weak_topic_counts(client, admin, other) == []


def test_weak_topics_ignore_exams_older_than_the_last_3(client, admin, student, subjects, enter):
    turkce, mat = subjects[0], subjects[4]
    # Entered out of date order: the two oldest exams fall outside the last 3.
    enter(student, "2026-11-01", [10, 5, 5, 5, 10, 10], wrong_topics={4: 1})
    enter(student, "2026-07-01", [10, 5, 5, 5, 10, 10], wrong_topics={0: 1})
    enter(student, "2026-08-01", [10, 5, 5, 5, 10, 10], wrong_topics={0: 1})
    enter(student, "2026-09-01", [10, 5, 5, 5, 10, 10], wrong_topics={0: 1, 4: 1})
    enter(student, "2026-10-01", [10, 5, 5, 5, 10, 10])

    # Turkish: missed 3 times overall but only once in the last 3 exams.
    assert weak_topic_counts(client, admin, student) == [(mat["topics"][0]["id"], 2)]


def test_a_topic_missed_once_is_not_weak(client, admin, student, enter):
    enter(student, "2026-09-01", [10, 5, 5, 5, 10, 10], wrong_topics={0: 13})

    assert weak_topic_counts(client, admin, student) == []


def test_all_weak_topics_are_listed(client, admin, student, enter):
    enter(student, "2026-09-01", [10, 5, 5, 5, 10, 10], wrong_topics={0: 13})
    enter(student, "2026-10-01", [10, 5, 5, 5, 10, 10], wrong_topics={0: 13})

    assert len(weak_topic_counts(client, admin, student)) == 13


def test_averages_compare_student_with_everyone_on_the_same_exams(client, admin, student, subjects, enter):
    ali = make_user(Role.student, "ali@test.dev", "Ali Can")
    can = make_user(Role.student, "can@test.dev", "Can Er")
    exam_1 = enter(student, "2026-09-01", [10, 4, 5, 5, 10, 10])
    enter(ali, "2026-09-01", [16, 8, 5, 5, 10, 10], exam_id=exam_1)
    enter(can, "2026-09-01", [19, 9, 5, 5, 10, 10], exam_id=exam_1)
    exam_2 = enter(student, "2026-10-01", [14, 6, 5, 5, 10, 10])
    enter(ali, "2026-10-01", [20, 10, 5, 5, 10, 10], exam_id=exam_2)
    # An exam this student did not take is left out of the class average.
    enter(ali, "2026-11-01", [0, 0, 0, 0, 0, 0])

    averages = analytics(client, admin, student.id).json()["averages"]

    assert [a["subject_id"] for a in averages] == [s["id"] for s in subjects]
    # Türkçe: student (10 + 14) / 2; class (10 + 16 + 19 + 14 + 20) / 5.
    assert averages[0] == {"subject_id": subjects[0]["id"], "student_average": 12.0, "class_average": 15.8}
    # İnkılap: student (4 + 6) / 2; class (4 + 8 + 9 + 6 + 10) / 5.
    assert averages[1] == {"subject_id": subjects[1]["id"], "student_average": 5.0, "class_average": 7.4}
    assert averages[2]["student_average"] == averages[2]["class_average"] == 5.0


def test_averages_for_a_student_alone_equal_their_own(client, admin, student, enter):
    enter(student, "2026-09-01", [10, 4, 5, 5, 10, 10])

    averages = analytics(client, admin, student.id).json()["averages"]

    assert all(a["student_average"] == a["class_average"] for a in averages)
