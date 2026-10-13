from datetime import date, timedelta
from fractions import Fraction

from fastapi import APIRouter, Depends
from sqlalchemy import func, select

from app.api.deps import DbSession, require_role
from app.models import Exam, ExamResult, QuestionLog, Role, User
from app.schemas.overview import OverviewExam, OverviewRow
from app.services.scoring import exact_net, round_net
from app.services.weak_topics import find_weak_topics

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_role(Role.admin))])

WEEK_DAYS = 7
# A student with no question log in this many days (today included) gets a warning.
NO_LOG_WARNING_DAYS = 3


def last_exams(db: DbSession, student_ids: list[int]) -> dict[int, OverviewExam]:
    """Each student's latest exam with the change from the one before it."""
    rows = db.execute(
        select(ExamResult.student_id, Exam.id, Exam.name, Exam.exam_date, ExamResult.correct, ExamResult.wrong)
        .join(Exam, Exam.id == ExamResult.exam_id)
        .where(ExamResult.student_id.in_(student_ids))
        .order_by(ExamResult.student_id, Exam.exam_date.desc(), Exam.id.desc())
    )
    # Per student: exams newest first, each with its unrounded total net.
    exams: dict[int, dict[int, list]] = {}
    for student_id, exam_id, name, exam_date, correct, wrong in rows:
        exam = exams.setdefault(student_id, {}).setdefault(exam_id, [name, exam_date, Fraction(0)])
        exam[2] += exact_net(correct, wrong)

    result = {}
    for student_id, by_exam in exams.items():
        (exam_id, (name, exam_date, net)), *older = by_exam.items()
        result[student_id] = OverviewExam(
            exam_id=exam_id,
            name=name,
            exam_date=exam_date,
            total_net=round_net(net),
            change=round_net(net - older[0][1][2]) if older else None,
        )
    return result


@router.get("/overview", response_model=list[OverviewRow])
def overview(db: DbSession):
    """One row per active student, by name."""
    students = db.scalars(
        select(User).where(User.role == Role.student, User.is_active).order_by(User.full_name, User.id)
    ).all()
    ids = [student.id for student in students]
    today = date.today()

    exams = last_exams(db, ids)
    in_week = QuestionLog.log_date.between(today - timedelta(days=WEEK_DAYS - 1), today)
    logs = {
        student_id: (last_log_date, week_solved)
        for student_id, last_log_date, week_solved in db.execute(
            select(
                QuestionLog.student_id,
                func.max(QuestionLog.log_date),
                func.coalesce(func.sum(QuestionLog.solved).filter(in_week), 0),
            )
            .where(QuestionLog.student_id.in_(ids))
            .group_by(QuestionLog.student_id)
        )
    }
    weak_topics = find_weak_topics(db, ids)

    warning_since = today - timedelta(days=NO_LOG_WARNING_DAYS - 1)
    rows = []
    for student in students:
        last_log_date, week_solved = logs.get(student.id, (None, 0))
        rows.append(
            OverviewRow(
                student_id=student.id,
                full_name=student.full_name,
                class_name=student.class_name,
                last_exam=exams.get(student.id),
                week_solved=week_solved,
                weak_topic_count=len(weak_topics.get(student.id, [])),
                last_log_date=last_log_date,
                no_recent_log=last_log_date is None or last_log_date < warning_since,
            )
        )
    return rows
