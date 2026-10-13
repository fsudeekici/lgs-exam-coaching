from datetime import date, timedelta

from sqlalchemy import func, select

from app.database import SessionLocal
from app.models import (
    CoachNote,
    Exam,
    ExamResult,
    ExamTopicMistake,
    MeetingNote,
    QuestionLog,
    Role,
    Subject,
    TopicProgress,
    TopicStatus,
)
from app.seed import DEMO_EXAMS, seed_demo_exams, seed_demo_meeting_notes, seed_demo_notes, seed_demo_study
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
        assert db.scalar(select(func.max(Exam.exam_date))) < date.today()
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


def study_counts(db, student_id):
    return (
        db.scalar(select(func.count()).select_from(QuestionLog).where(QuestionLog.student_id == student_id)),
        db.scalar(select(func.count()).select_from(TopicProgress).where(TopicProgress.student_id == student_id)),
    )


def test_demo_study_data_covers_the_last_30_days(student):
    other = make_user(Role.student, "ali@test.dev", "Ali Can")

    with SessionLocal() as db:
        seed_demo_study(db, [student, other])
        db.commit()

        today = date.today()
        for who in (student, other):
            logs = db.scalars(select(QuestionLog).where(QuestionLog.student_id == who.id)).all()
            days = {log.log_date for log in logs}
            assert min(days) >= today - timedelta(days=29) and max(days) <= today
            # Most days have entries, but not all: there are days off.
            assert 15 <= len(days) <= 30
            assert all(0 < log.solved and log.correct + log.wrong <= log.solved for log in logs)
            statuses = set(db.scalars(select(TopicProgress.status).where(TopicProgress.student_id == who.id)))
            assert statuses == {TopicStatus.studying, TopicStatus.done, TopicStatus.needs_review}


def test_demo_study_data_is_not_added_twice_or_over_existing_data(student):
    other = make_user(Role.student, "ali@test.dev", "Ali Can")

    with SessionLocal() as db:
        # `other` already uses the app: one log, no topic progress.
        subject = db.scalars(select(Subject)).first()
        db.add(QuestionLog(student_id=other.id, log_date=date.today(), subject_id=subject.id, solved=5, correct=5, wrong=0))
        db.commit()

        seed_demo_study(db, [student, other])
        db.commit()
        first = study_counts(db, student.id)
        seed_demo_study(db, [student, other])
        db.commit()

        assert study_counts(db, student.id) == first
        assert first[0] > 0 and first[1] > 0
        # Their own log is left alone; the missing topic progress is filled in.
        other_logs, other_progress = study_counts(db, other.id)
        assert other_logs == 1 and other_progress > 0


def test_demo_notes_are_added_once(student):
    with SessionLocal() as db:
        seed_demo_notes(db, student)
        seed_demo_notes(db, student)
        db.commit()

        notes = db.scalars(select(CoachNote).where(CoachNote.student_id == student.id)).all()
        assert sorted(n.visible_to_parent for n in notes) == [False, True]


def test_demo_meeting_notes_are_added_once_with_past_dates(student):
    with SessionLocal() as db:
        seed_demo_meeting_notes(db, student)
        seed_demo_meeting_notes(db, student)
        db.commit()

        notes = db.scalars(select(MeetingNote).where(MeetingNote.student_id == student.id)).all()
        assert len(notes) == 2
        assert all(n.meeting_date < date.today() for n in notes)
