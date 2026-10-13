from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, Computed, DateTime, ForeignKey, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Exam(Base):
    """A mock (practice) exam sitting."""

    __tablename__ = "exams"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    exam_date: Mapped[date]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ExamResult(Base):
    """One student's result for one subject of one exam."""

    __tablename__ = "exam_results"
    __table_args__ = (
        UniqueConstraint("exam_id", "student_id", "subject_id"),
        CheckConstraint("correct >= 0 AND wrong >= 0 AND blank >= 0", name="ck_exam_results_non_negative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    exam_id: Mapped[int] = mapped_column(ForeignKey("exams.id", ondelete="CASCADE"), index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id"))
    correct: Mapped[int]
    wrong: Mapped[int]
    blank: Mapped[int]
    # LGS rule: every 3 wrong answers cancel 1 correct answer.
    # Keep in sync with app.services.scoring.calculate_net.
    net: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), Computed("round(correct - wrong / 3.0, 2)", persisted=True)
    )
