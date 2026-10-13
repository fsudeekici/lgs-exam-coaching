from sqlalchemy import func, select

from app.database import SessionLocal
from app.models import Exam, ExamResult, ExamTopicMistake, Role, Subject
from app.seed import DEMO_EXAMS, seed_demo_exams
from tests.conftest import make_user


def snapshot(db):
    rows = db.execute(
        select(Exam.name, ExamResult.student_id, ExamResult.subject_id, ExamResult.correct, ExamResult.wrong)
        .join(Exam, Exam.id == ExamResult.exam_id)
        .order_by(Exam.name, ExamResult.student_id, ExamResult.subject_id)
    )
    return [tuple(row) for row in rows]


def test_demo_exams_have_valid_results_for_every_student(student):
    other = make_user(Role.student, "ali@test.dev", "Ali Can")

    with SessionLocal() as db:
        seed_demo_exams(db, [student, other])
        db.commit()

        assert [e.name for e in db.scalars(select(Exam).order_by(Exam.exam_date))] == [name for name, _, _ in DEMO_EXAMS]
        results = db.execute(select(ExamResult, Subject).join(Subject, Subject.id == ExamResult.subject_id)).all()
        # 4 exams x 2 students x 6 subjects
        assert len(results) == 48
        for result, subject in results:
            assert min(result.correct, result.wrong, result.blank) >= 0
            assert result.correct + result.wrong + result.blank == subject.question_count
        assert db.scalar(select(func.count()).select_from(ExamTopicMistake)) > 0


def test_demo_exams_are_not_duplicated_or_changed_on_reseed(student):
    with SessionLocal() as db:
        seed_demo_exams(db, [student])
        db.commit()
        first = snapshot(db)

        # A missing exam is recreated with the same numbers; the others are left alone.
        db.delete(db.scalar(select(Exam).where(Exam.name == DEMO_EXAMS[2][0])))
        db.commit()
        seed_demo_exams(db, [student])
        seed_demo_exams(db, [student])
        db.commit()

        assert db.scalar(select(func.count()).select_from(Exam)) == 4
        assert snapshot(db) == first
