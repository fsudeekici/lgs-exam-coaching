from datetime import date, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func, select

from app.api.admin_analytics import build_student_analytics
from app.api.deps import DbSession, require_role
from app.models import CoachNote, QuestionLog, Role, User
from app.schemas.parent import ChildSummary, DayQuestions, QuestionsSummary

router = APIRouter(prefix="/parent", tags=["parent"])

CurrentParent = Annotated[User, Depends(require_role(Role.parent))]


def questions_summary(db: DbSession, student_id: int, days: int = 7) -> QuestionsSummary:
    """Questions per day over the last `days` days, today included."""
    today = date.today()
    first_day = today - timedelta(days=days - 1)
    rows = db.execute(
        select(
            QuestionLog.log_date,
            func.sum(QuestionLog.solved),
            func.sum(QuestionLog.correct),
            func.sum(QuestionLog.wrong),
        )
        .where(QuestionLog.student_id == student_id, QuestionLog.log_date.between(first_day, today))
        .group_by(QuestionLog.log_date)
    )
    by_day = {log_date: (solved, correct, wrong) for log_date, solved, correct, wrong in rows}
    days = [
        DayQuestions(day=day, solved=solved, correct=correct, wrong=wrong)
        for day in (first_day + timedelta(days=offset) for offset in range(days))
        for solved, correct, wrong in [by_day.get(day, (0, 0, 0))]
    ]
    return QuestionsSummary(
        solved=sum(d.solved for d in days),
        correct=sum(d.correct for d in days),
        wrong=sum(d.wrong for d in days),
        active_days=len(by_day),
        days=days,
    )


def visible_notes(db: DbSession, student_id: int) -> list[CoachNote]:
    """Coach notes marked visible to parents, newest first."""
    return list(
        db.scalars(
            select(CoachNote)
            .where(CoachNote.student_id == student_id, CoachNote.visible_to_parent)
            .order_by(CoachNote.created_at.desc(), CoachNote.id.desc())
        )
    )


@router.get("/children", response_model=list[ChildSummary])
def my_children(parent: CurrentParent, db: DbSession):
    """A summary for each active student linked to the logged-in parent."""
    children = []
    for student in parent.students:
        if not student.is_active:
            continue
        children.append(
            ChildSummary(
                analytics=build_student_analytics(db, student),
                week=questions_summary(db, student.id),
                notes=visible_notes(db, student.id),
            )
        )
    return children
