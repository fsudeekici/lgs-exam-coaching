import enum
from datetime import date, datetime

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Index, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class TopicStatus(str, enum.Enum):
    not_started = "not_started"
    studying = "studying"
    done = "done"
    needs_review = "needs_review"


class QuestionLog(Base):
    """Questions a student solved on one day, for a subject and optionally one of its topics."""

    __tablename__ = "question_logs"
    __table_args__ = (
        CheckConstraint(
            "solved > 0 AND correct >= 0 AND wrong >= 0 AND correct + wrong <= solved",
            name="ck_question_logs_counts",
        ),
        Index("ix_question_logs_student_id_log_date", "student_id", "log_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    log_date: Mapped[date]
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id", ondelete="CASCADE"))
    # Empty for mixed practice that does not belong to a single topic.
    topic_id: Mapped[int | None] = mapped_column(ForeignKey("topics.id", ondelete="SET NULL"))
    solved: Mapped[int]
    correct: Mapped[int]
    wrong: Mapped[int]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class TopicProgress(Base):
    """Where a student stands on a topic. No row means not started."""

    __tablename__ = "topic_progress"

    student_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    topic_id: Mapped[int] = mapped_column(ForeignKey("topics.id", ondelete="CASCADE"), primary_key=True, index=True)
    status: Mapped[TopicStatus] = mapped_column(Enum(TopicStatus, name="topic_status"))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
