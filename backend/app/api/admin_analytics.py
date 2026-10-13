from collections import defaultdict
from fractions import Fraction

from fastapi import APIRouter, Depends
from sqlalchemy import func, select

from app.api.admin_users import get_user_or_404
from app.api.deps import DbSession, require_role
from app.models import Exam, ExamResult, ExamTopicMistake, Role, Subject, Topic
from app.schemas.analytics import (
    Comparison,
    ExamPoint,
    NetChange,
    StudentAnalytics,
    SubjectAverage,
    SubjectChange,
    SubjectNet,
    WeakTopic,
)
from app.services.scoring import exact_net, round_net

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_role(Role.admin))])

WEAK_TOPIC_LIMIT = 10


def net_change(last: Fraction, previous: Fraction | None) -> dict:
    """Rounded values plus their change, taken from the unrounded nets so it is not off by 0.01."""
    if previous is None:
        return {"last": round_net(last), "previous": None, "change": None}
    return {"last": round_net(last), "previous": round_net(previous), "change": round_net(last - previous)}


def compare_last_two(exams: list[ExamPoint], nets: dict[int, dict[int, Fraction]]) -> Comparison | None:
    """`nets` holds the unrounded net per exam id and subject id."""
    if not exams:
        return None
    last = nets[exams[-1].exam_id]
    previous = nets[exams[-2].exam_id] if len(exams) > 1 else None
    return Comparison(
        last_exam_id=exams[-1].exam_id,
        previous_exam_id=exams[-2].exam_id if previous is not None else None,
        total=NetChange(**net_change(sum(last.values()), sum(previous.values()) if previous is not None else None)),
        subjects=[
            SubjectChange(subject_id=subject_id, **net_change(net, previous.get(subject_id) if previous else None))
            for subject_id, net in last.items()
        ],
    )


@router.get("/students/{student_id}/analytics", response_model=StudentAnalytics)
def student_analytics(student_id: int, db: DbSession):
    """Everything the student detail page shows, in one response."""
    student = get_user_or_404(db, student_id, Role.student)
    subjects = db.scalars(select(Subject).order_by(Subject.display_order)).all()

    # Net trend: the student's exams, oldest first, subjects in booklet order.
    rows = db.execute(
        select(ExamResult, Exam)
        .join(Exam, Exam.id == ExamResult.exam_id)
        .join(Subject, Subject.id == ExamResult.subject_id)
        .where(ExamResult.student_id == student_id)
        .order_by(Exam.exam_date, Exam.id, Subject.display_order)
    )
    points: dict[int, ExamPoint] = {}
    nets: dict[int, dict[int, Fraction]] = defaultdict(dict)
    for result, exam in rows:
        point = points.setdefault(
            exam.id, ExamPoint(exam_id=exam.id, name=exam.name, exam_date=exam.exam_date, total_net=0, nets=[])
        )
        nets[exam.id][result.subject_id] = exact_net(result.correct, result.wrong)
        point.nets.append(SubjectNet(subject_id=result.subject_id, net=float(result.net)))
        point.total_net = round_net(sum(nets[exam.id].values()))
    exams = list(points.values())

    weak_topics = db.execute(
        select(Topic.id, Topic.name, Topic.subject_id, func.count().label("count"))
        .join(ExamTopicMistake, ExamTopicMistake.topic_id == Topic.id)
        .join(ExamResult, ExamResult.id == ExamTopicMistake.exam_result_id)
        .where(ExamResult.student_id == student_id)
        .group_by(Topic.id)
        .order_by(func.count().desc(), Topic.id)
        .limit(WEAK_TOPIC_LIMIT)
    )

    # Student vs everyone, over the exams this student took so both sides cover the same exams.
    student_average = func.avg(ExamResult.net).filter(ExamResult.student_id == student_id)
    averages = db.execute(
        select(ExamResult.subject_id, student_average, func.avg(ExamResult.net))
        .join(Subject, Subject.id == ExamResult.subject_id)
        .where(ExamResult.exam_id.in_(points.keys()))
        .group_by(ExamResult.subject_id, Subject.display_order)
        .order_by(Subject.display_order)
    )

    return StudentAnalytics(
        student=student,
        subjects=subjects,
        exams=exams,
        comparison=compare_last_two(exams, nets),
        weak_topics=[
            WeakTopic(topic_id=topic_id, name=name, subject_id=subject_id, count=count)
            for topic_id, name, subject_id, count in weak_topics
        ],
        averages=[
            SubjectAverage(
                subject_id=subject_id,
                student_average=round(float(student_avg), 2),
                class_average=round(float(class_avg), 2),
            )
            for subject_id, student_avg, class_avg in averages
        ],
    )
