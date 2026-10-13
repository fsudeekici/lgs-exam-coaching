from datetime import date, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select

from app.api.admin import list_subjects
from app.api.admin_analytics import build_student_analytics
from app.api.deps import DbSession, require_role
from app.models import QuestionLog, Role, Subject, Topic, TopicProgress, User
from app.schemas.analytics import StudentAnalytics
from app.schemas.exam import SubjectOut
from app.schemas.study import QuestionLogIn, QuestionLogOut, TopicProgressIn, TopicProgressOut

# Everything here acts on the logged-in student's own data.
router = APIRouter(prefix="/student", tags=["student"])

CurrentStudent = Annotated[User, Depends(require_role(Role.student))]
Days = Annotated[int, Query(ge=1, le=365)]


def list_question_logs(db: DbSession, student_id: int, days: int) -> list[QuestionLog]:
    """A student's logs from the last `days` days (today included), newest first."""
    since = date.today() - timedelta(days=days - 1)
    return list(
        db.scalars(
            select(QuestionLog)
            .where(QuestionLog.student_id == student_id, QuestionLog.log_date >= since)
            .order_by(QuestionLog.log_date.desc(), QuestionLog.id.desc())
        )
    )


def list_topic_progress(db: DbSession, student_id: int) -> list[TopicProgress]:
    return list(db.scalars(select(TopicProgress).where(TopicProgress.student_id == student_id)))


@router.get("/subjects", response_model=list[SubjectOut])
def subjects(student: CurrentStudent, db: DbSession):
    """Subjects with their topics, for the log form and the topic list."""
    return list_subjects(db)


@router.get("/question-logs", response_model=list[QuestionLogOut])
def my_question_logs(student: CurrentStudent, db: DbSession, days: Days = 30):
    return list_question_logs(db, student.id, days)


@router.post("/question-logs", response_model=QuestionLogOut, status_code=status.HTTP_201_CREATED)
def add_question_log(payload: QuestionLogIn, student: CurrentStudent, db: DbSession):
    # One day of slack for time zone differences between the student and the server.
    if payload.log_date > date.today() + timedelta(days=1):
        raise HTTPException(status_code=422, detail="İleri bir tarih için kayıt girilemez")
    if db.get(Subject, payload.subject_id) is None:
        raise HTTPException(status_code=422, detail="Ders bulunamadı")
    if payload.topic_id is not None:
        topic = db.get(Topic, payload.topic_id)
        if topic is None or topic.subject_id != payload.subject_id:
            raise HTTPException(status_code=422, detail="Seçilen konu bu derse ait değil")

    log = QuestionLog(student_id=student.id, **payload.model_dump())
    db.add(log)
    db.commit()
    return log


@router.delete("/question-logs/{log_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_question_log(log_id: int, student: CurrentStudent, db: DbSession) -> None:
    log = db.get(QuestionLog, log_id)
    if log is None or log.student_id != student.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kayıt bulunamadı")
    db.delete(log)
    db.commit()


@router.get("/topic-progress", response_model=list[TopicProgressOut])
def my_topic_progress(student: CurrentStudent, db: DbSession):
    """Only topics the student has marked; every other topic is not started."""
    return list_topic_progress(db, student.id)


@router.put("/topic-progress/{topic_id}", response_model=TopicProgressOut)
def set_topic_progress(topic_id: int, payload: TopicProgressIn, student: CurrentStudent, db: DbSession):
    if db.get(Topic, topic_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Konu bulunamadı")
    progress = db.get(TopicProgress, (student.id, topic_id))
    if progress is None:
        progress = TopicProgress(student_id=student.id, topic_id=topic_id)
        db.add(progress)
    progress.status = payload.status
    db.commit()
    return progress


@router.get("/analytics", response_model=StudentAnalytics)
def my_analytics(student: CurrentStudent, db: DbSession):
    """The same exam analytics the admin sees for this student."""
    return build_student_analytics(db, student)
