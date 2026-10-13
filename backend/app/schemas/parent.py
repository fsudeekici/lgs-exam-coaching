from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.analytics import StudentAnalytics


class NoteIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    body: str = Field(min_length=1, max_length=2000)
    visible_to_parent: bool = False


class NoteUpdate(BaseModel):
    """Fields left out stay unchanged."""

    model_config = ConfigDict(str_strip_whitespace=True)

    body: str | None = Field(default=None, min_length=1, max_length=2000)
    visible_to_parent: bool | None = None


class NoteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    body: str
    visible_to_parent: bool
    created_at: datetime


class ParentNote(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    body: str
    created_at: datetime


class DayQuestions(BaseModel):
    day: date
    solved: int
    correct: int
    wrong: int


class WeekSummary(BaseModel):
    """Questions solved over the last 7 days, today included."""

    solved: int
    correct: int
    wrong: int
    # Days with at least one entry.
    active_days: int
    # All 7 days, oldest first; days without entries are zero.
    days: list[DayQuestions]


class ChildSummary(BaseModel):
    """What a parent sees for one of their children."""

    analytics: StudentAnalytics
    week: WeekSummary
    # Only notes the coach marked as visible to parents, newest first.
    notes: list[ParentNote]
