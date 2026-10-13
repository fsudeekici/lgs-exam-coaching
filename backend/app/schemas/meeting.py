from datetime import date, datetime
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field

from app.schemas.analytics import StudentAnalytics
from app.schemas.parent import ParentNote, QuestionsSummary


def not_in_future(value: date) -> date:
    if value > date.today():
        raise ValueError("Görüşme tarihi ileri bir tarih olamaz")
    return value


class MeetingNoteIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    meeting_date: Annotated[date, AfterValidator(not_in_future)]
    body: str = Field(min_length=1, max_length=4000)


class MeetingNoteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    meeting_date: date
    body: str
    created_at: datetime


class SubjectQuestions(BaseModel):
    subject_id: int
    solved: int
    correct: int
    wrong: int


class SubjectProgress(BaseModel):
    """How many of a subject's topics are in each status."""

    subject_id: int
    total: int
    not_started: int
    studying: int
    done: int
    needs_review: int


class MeetingPage(BaseModel):
    """Everything the parent meeting page shows for one student."""

    analytics: StudentAnalytics
    # The last 30 days.
    questions: QuestionsSummary
    # Same period, per subject in booklet order; subjects without entries are left out.
    questions_by_subject: list[SubjectQuestions]
    # Every subject, in booklet order.
    topic_progress: list[SubjectProgress]
    # Only coach notes marked visible to parents, newest first.
    notes: list[ParentNote]
    # Latest meeting first.
    meeting_notes: list[MeetingNoteOut]
