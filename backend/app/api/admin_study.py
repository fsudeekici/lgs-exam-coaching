from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from app.api.admin_users import get_user_or_404
from app.api.deps import DbSession, require_role
from app.api.student import Days, list_question_logs, list_topic_progress
from app.models import CoachNote, Role, User
from app.schemas.parent import NoteIn, NoteOut, NoteUpdate
from app.schemas.study import QuestionLogOut, TopicProgressOut

# Admin views of what a student records in the student panel, and the coach's notes about them.
router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_role(Role.admin))])


@router.get("/students/{student_id}/question-logs", response_model=list[QuestionLogOut])
def student_question_logs(student_id: int, db: DbSession, days: Days = 30):
    return list_question_logs(db, get_user_or_404(db, student_id, Role.student).id, days)


@router.get("/students/{student_id}/topic-progress", response_model=list[TopicProgressOut])
def student_topic_progress(student_id: int, db: DbSession):
    return list_topic_progress(db, get_user_or_404(db, student_id, Role.student).id)


def get_note_or_404(db: DbSession, note_id: int) -> CoachNote:
    note = db.get(CoachNote, note_id)
    if note is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not bulunamadı")
    return note


@router.get("/students/{student_id}/notes", response_model=list[NoteOut])
def student_notes(student_id: int, db: DbSession):
    """All coach notes for a student, newest first."""
    get_user_or_404(db, student_id, Role.student)
    return db.scalars(
        select(CoachNote)
        .where(CoachNote.student_id == student_id)
        .order_by(CoachNote.created_at.desc(), CoachNote.id.desc())
    ).all()


@router.post("/students/{student_id}/notes", response_model=NoteOut, status_code=status.HTTP_201_CREATED)
def add_note(
    student_id: int, payload: NoteIn, admin: Annotated[User, Depends(require_role(Role.admin))], db: DbSession
):
    get_user_or_404(db, student_id, Role.student)
    note = CoachNote(student_id=student_id, author_id=admin.id, **payload.model_dump())
    db.add(note)
    db.commit()
    return note


@router.patch("/notes/{note_id}", response_model=NoteOut)
def update_note(note_id: int, payload: NoteUpdate, db: DbSession):
    """Edit a note or change whether the parent can see it."""
    note = get_note_or_404(db, note_id)
    if payload.body is not None:
        note.body = payload.body
    if payload.visible_to_parent is not None:
        note.visible_to_parent = payload.visible_to_parent
    db.commit()
    return note


@router.delete("/notes/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_note(note_id: int, db: DbSession) -> None:
    db.delete(get_note_or_404(db, note_id))
    db.commit()
