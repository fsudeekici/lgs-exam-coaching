from datetime import date, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select

from app.api.admin_analytics import build_student_analytics
from app.api.admin_users import get_user_or_404
from app.api.deps import DbSession, require_role
from app.api.parent import questions_summary, visible_notes
from app.models import MeetingNote, QuestionLog, Role, Subject, Topic, TopicProgress, TopicStatus, User
from app.schemas.meeting import MeetingNoteIn, MeetingNoteOut, MeetingPage, SubjectProgress, SubjectQuestions

# The page the coach shows (or prints) at a parent meeting, and the notes taken afterwards.
router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_role(Role.admin))])

MEETING_DAYS = 30


def questions_by_subject(db: DbSession, student_id: int, days: int) -> list[SubjectQuestions]:
    today = date.today()
    rows = db.execute(
        select(
            QuestionLog.subject_id,
            func.sum(QuestionLog.solved),
            func.sum(QuestionLog.correct),
            func.sum(QuestionLog.wrong),
        )
        .join(Subject, Subject.id == QuestionLog.subject_id)
        .where(
            QuestionLog.student_id == student_id,
            QuestionLog.log_date.between(today - timedelta(days=days - 1), today),
        )
        .group_by(QuestionLog.subject_id, Subject.display_order)
        .order_by(Subject.display_order)
    )
    return [
        SubjectQuestions(subject_id=subject_id, solved=solved, correct=correct, wrong=wrong)
        for subject_id, solved, correct, wrong in rows
    ]


def topic_progress_by_subject(db: DbSession, student_id: int) -> list[SubjectProgress]:
    totals = db.execute(
        select(Subject.id, func.count(Topic.id))
        .outerjoin(Topic, Topic.subject_id == Subject.id)
        .group_by(Subject.id)
        .order_by(Subject.display_order)
    ).all()
    marked: dict[int, dict[TopicStatus, int]] = {}
    for subject_id, topic_status, count in db.execute(
        select(Topic.subject_id, TopicProgress.status, func.count())
        .join(Topic, Topic.id == TopicProgress.topic_id)
        .where(TopicProgress.student_id == student_id)
        .group_by(Topic.subject_id, TopicProgress.status)
    ):
        marked.setdefault(subject_id, {})[topic_status] = count

    progress = []
    for subject_id, total in totals:
        counts = marked.get(subject_id, {})
        studying, done, needs_review = (
            counts.get(s, 0) for s in (TopicStatus.studying, TopicStatus.done, TopicStatus.needs_review)
        )
        progress.append(
            SubjectProgress(
                subject_id=subject_id,
                total=total,
                # Topics without a row, plus any the student set back to not started.
                not_started=total - studying - done - needs_review,
                studying=studying,
                done=done,
                needs_review=needs_review,
            )
        )
    return progress


@router.get("/students/{student_id}/meeting", response_model=MeetingPage)
def meeting_page(student_id: int, db: DbSession):
    student = get_user_or_404(db, student_id, Role.student)
    return MeetingPage(
        analytics=build_student_analytics(db, student),
        questions=questions_summary(db, student.id, MEETING_DAYS),
        questions_by_subject=questions_by_subject(db, student.id, MEETING_DAYS),
        topic_progress=topic_progress_by_subject(db, student.id),
        notes=visible_notes(db, student.id),
        meeting_notes=db.scalars(
            select(MeetingNote)
            .where(MeetingNote.student_id == student.id)
            .order_by(MeetingNote.meeting_date.desc(), MeetingNote.id.desc())
        ).all(),
    )


@router.post(
    "/students/{student_id}/meeting-notes", response_model=MeetingNoteOut, status_code=status.HTTP_201_CREATED
)
def add_meeting_note(
    student_id: int,
    payload: MeetingNoteIn,
    admin: Annotated[User, Depends(require_role(Role.admin))],
    db: DbSession,
):
    get_user_or_404(db, student_id, Role.student)
    note = MeetingNote(student_id=student_id, author_id=admin.id, **payload.model_dump())
    db.add(note)
    db.commit()
    return note


@router.delete("/meeting-notes/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_meeting_note(note_id: int, db: DbSession) -> None:
    note = db.get(MeetingNote, note_id)
    if note is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not bulunamadı")
    db.delete(note)
    db.commit()
