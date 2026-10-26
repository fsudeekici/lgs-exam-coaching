from collections import defaultdict
from fractions import Fraction

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.api.admin_users import get_user_or_404
from app.api.deps import CurrentAdmin, DbSession, require_admin
from app.models import Exam, ExamResult, ExamTopicMistake, Role, Subject, User
from app.schemas.exam import (
    ExamCreate,
    ExamDetail,
    ExamOut,
    ResultOut,
    StudentResultsIn,
    StudentResultsOut,
    SubjectOut,
)
from app.services.coaching import students_of
from app.services.scoring import exact_net, round_net

# Exams are shared by all admins; each admin only sees and enters results for their own students.
router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])


def invalid(detail: str) -> HTTPException:
    return HTTPException(status_code=422, detail=detail)


def get_exam_or_404(db: DbSession, exam_id: int) -> Exam:
    exam = db.get(Exam, exam_id)
    if exam is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deneme bulunamadı")
    return exam


def load_student_results(
    db: DbSession, admin: User, exam_id: int, student_id: int | None = None
) -> list[StudentResultsOut]:
    """Results of an exam grouped per student (the admin's own students only), ordered by student name."""
    query = (
        select(ExamResult, User.full_name)
        .join(User, User.id == ExamResult.student_id)
        .join(Subject, Subject.id == ExamResult.subject_id)
        .where(ExamResult.exam_id == exam_id, students_of(admin))
        .options(selectinload(ExamResult.topic_mistakes))
        .order_by(User.full_name, User.id, Subject.display_order)
    )
    if student_id is not None:
        query = query.where(ExamResult.student_id == student_id)

    students: dict[int, StudentResultsOut] = {}
    totals: dict[int, Fraction] = defaultdict(Fraction)
    for result, full_name in db.execute(query):
        entry = students.setdefault(
            result.student_id,
            StudentResultsOut(student_id=result.student_id, full_name=full_name, total_net=0, results=[]),
        )
        entry.results.append(
            ResultOut(
                subject_id=result.subject_id,
                correct=result.correct,
                wrong=result.wrong,
                blank=result.blank,
                net=float(result.net),
                mistake_topic_ids=[m.topic_id for m in result.topic_mistakes],
            )
        )
        totals[result.student_id] += exact_net(result.correct, result.wrong)
        entry.total_net = round_net(totals[result.student_id])
    return list(students.values())


@router.get("/subjects", response_model=list[SubjectOut])
def list_subjects(db: DbSession):
    return db.scalars(select(Subject).options(selectinload(Subject.topics)).order_by(Subject.display_order)).all()


@router.get("/exams", response_model=list[ExamOut])
def list_exams(db: DbSession, admin: CurrentAdmin):
    """Every exam; `student_count` only counts the admin's own students."""
    own_results = (
        select(ExamResult.exam_id, ExamResult.student_id)
        .join(User, User.id == ExamResult.student_id)
        .where(students_of(admin))
        .subquery()
    )
    rows = db.execute(
        select(Exam, func.count(func.distinct(own_results.c.student_id)))
        .outerjoin(own_results, own_results.c.exam_id == Exam.id)
        .group_by(Exam.id)
        .order_by(Exam.exam_date.desc(), Exam.id.desc())
    )
    return [
        ExamOut(id=e.id, name=e.name, exam_date=e.exam_date, publisher=e.publisher, student_count=count)
        for e, count in rows
    ]


@router.post("/exams", response_model=ExamOut, status_code=status.HTTP_201_CREATED)
def create_exam(payload: ExamCreate, db: DbSession):
    exam = Exam(name=payload.name, exam_date=payload.exam_date, publisher=payload.publisher)
    db.add(exam)
    db.commit()
    return ExamOut(id=exam.id, name=exam.name, exam_date=exam.exam_date, publisher=exam.publisher, student_count=0)


@router.get("/exams/{exam_id}", response_model=ExamDetail)
def get_exam(exam_id: int, db: DbSession, admin: CurrentAdmin):
    exam = get_exam_or_404(db, exam_id)
    students = load_student_results(db, admin, exam_id)
    return ExamDetail(
        id=exam.id,
        name=exam.name,
        exam_date=exam.exam_date,
        publisher=exam.publisher,
        student_count=len(students),
        students=students,
    )


@router.put("/exams/{exam_id}/students/{student_id}/results", response_model=StudentResultsOut)
def save_student_results(
    exam_id: int, student_id: int, payload: StudentResultsIn, db: DbSession, admin: CurrentAdmin
):
    """Save one student's results for all subjects of an exam, replacing any earlier entry."""
    get_exam_or_404(db, exam_id)
    get_user_or_404(db, admin, student_id, Role.student)

    subjects = {s.id: s for s in db.scalars(select(Subject).options(selectinload(Subject.topics)))}
    submitted_ids = [r.subject_id for r in payload.results]
    if len(submitted_ids) != len(subjects) or set(submitted_ids) != set(subjects):
        raise invalid("Tüm dersler için sonuç girilmelidir")

    for item in payload.results:
        subject = subjects[item.subject_id]
        if item.correct + item.wrong + item.blank != subject.question_count:
            raise invalid(f"{subject.name}: doğru + yanlış + boş toplamı {subject.question_count} olmalıdır")
        if not set(item.mistake_topic_ids) <= {t.id for t in subject.topics}:
            raise invalid(f"{subject.name}: seçilen konu bu derse ait değil")

    existing = db.scalars(
        select(ExamResult).where(ExamResult.exam_id == exam_id, ExamResult.student_id == student_id)
    ).all()
    for result in existing:
        db.delete(result)
    db.flush()

    for item in payload.results:
        db.add(
            ExamResult(
                exam_id=exam_id,
                student_id=student_id,
                subject_id=item.subject_id,
                correct=item.correct,
                wrong=item.wrong,
                blank=item.blank,
                topic_mistakes=[ExamTopicMistake(topic_id=topic_id) for topic_id in set(item.mistake_topic_ids)],
            )
        )
    db.commit()
    return load_student_results(db, admin, exam_id, student_id)[0]


@router.delete("/exams/{exam_id}/students/{student_id}/results", status_code=status.HTTP_204_NO_CONTENT)
def delete_student_results(exam_id: int, student_id: int, db: DbSession, admin: CurrentAdmin) -> None:
    get_user_or_404(db, admin, student_id, Role.student)
    results = db.scalars(
        select(ExamResult).where(ExamResult.exam_id == exam_id, ExamResult.student_id == student_id)
    ).all()
    for result in results:
        db.delete(result)
    db.commit()
