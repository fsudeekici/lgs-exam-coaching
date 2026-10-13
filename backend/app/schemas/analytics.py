from datetime import date

from pydantic import BaseModel, ConfigDict


class AnalyticsStudent(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    school: str | None
    class_name: str | None
    is_active: bool


class AnalyticsSubject(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    short_name: str
    session: str
    question_count: int


class SubjectNet(BaseModel):
    subject_id: int
    net: float


class ExamPoint(BaseModel):
    """One exam the student took: a point on the trend chart."""

    exam_id: int
    name: str
    exam_date: date
    total_net: float
    nets: list[SubjectNet]


class NetChange(BaseModel):
    last: float
    # None when there is no previous exam, or the subject is missing from it.
    previous: float | None
    change: float | None


class SubjectChange(NetChange):
    subject_id: int


class Comparison(BaseModel):
    """The student's latest exam against the one before it."""

    last_exam_id: int
    previous_exam_id: int | None
    total: NetChange
    subjects: list[SubjectChange]


class WeakTopic(BaseModel):
    topic_id: int
    name: str
    subject_id: int
    count: int


class SubjectAverage(BaseModel):
    subject_id: int
    student_average: float
    # Average of every student who took the same exams, this student included.
    class_average: float


class StudentAnalytics(BaseModel):
    student: AnalyticsStudent
    subjects: list[AnalyticsSubject]
    # Oldest exam first.
    exams: list[ExamPoint]
    comparison: Comparison | None
    weak_topics: list[WeakTopic]
    averages: list[SubjectAverage]
