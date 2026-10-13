from datetime import date

from pydantic import BaseModel


class OverviewExam(BaseModel):
    exam_id: int
    name: str
    exam_date: date
    total_net: float
    # Against the student's previous exam; None when this is their first.
    change: float | None


class OverviewRow(BaseModel):
    """One active student on the admin home page."""

    student_id: int
    full_name: str
    class_name: str | None
    last_exam: OverviewExam | None
    # Questions solved in the last 7 days, today included.
    week_solved: int
    # Topics marked wrong in at least 2 of the student's last 3 exams.
    weak_topic_count: int
    last_log_date: date | None
    # True when the student has no question log in the last 3 days, today included.
    no_recent_log: bool
