from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Exam, ExamResult, ExamTopicMistake, Topic

# A topic is weak when the student got it wrong in at least MIN_MISSES of their last RECENT_EXAMS exams.
RECENT_EXAMS = 3
MIN_MISSES = 2


def find_weak_topics(db: Session, student_ids: list[int]) -> dict[int, list[tuple[Topic, int]]]:
    """Each student's weak topics with how many of their recent exams missed them, most missed first.

    Students without weak topics are left out.
    """
    # Each student's exams numbered from the latest; an exam has one result row per subject.
    recency = (
        func.dense_rank()
        .over(partition_by=ExamResult.student_id, order_by=(Exam.exam_date.desc(), Exam.id.desc()))
        .label("recency")
    )
    results = (
        select(ExamResult.id, ExamResult.student_id, recency)
        .join(Exam, Exam.id == ExamResult.exam_id)
        .where(ExamResult.student_id.in_(student_ids))
        .subquery()
    )
    # A topic can be marked once per exam, so the row count is the number of exams that missed it.
    misses = func.count().label("misses")
    rows = db.execute(
        select(results.c.student_id, Topic, misses)
        .join(ExamTopicMistake, ExamTopicMistake.exam_result_id == results.c.id)
        .join(Topic, Topic.id == ExamTopicMistake.topic_id)
        .where(results.c.recency <= RECENT_EXAMS)
        .group_by(results.c.student_id, Topic.id)
        .having(func.count() >= MIN_MISSES)
        .order_by(results.c.student_id, misses.desc(), Topic.id)
    )
    weak: dict[int, list[tuple[Topic, int]]] = {}
    for student_id, topic, count in rows:
        weak.setdefault(student_id, []).append((topic, count))
    return weak
