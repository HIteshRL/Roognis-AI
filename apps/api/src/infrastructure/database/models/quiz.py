from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base, TimestampMixin, UUIDMixin


class QuizModel(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "quizzes"

    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    subject: Mapped[str | None] = mapped_column(String(200), nullable=True)
    chapter: Mapped[str | None] = mapped_column(String(200), nullable=True)
    difficulty: Mapped[str] = mapped_column(
        String(10), nullable=False, default="medium"
    )
    question_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    total_attempts: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    best_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)


class QuizQuestionModel(Base, UUIDMixin):
    __tablename__ = "quiz_questions"

    quiz_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("quizzes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    concept_name: Mapped[str] = mapped_column(String(200), nullable=False)
    concept_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), nullable=True
    )
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    question_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="mcq"
    )
    options: Mapped[list] = mapped_column(JSONB, nullable=True, default=list)
    correct_answer: Mapped[str] = mapped_column(Text, nullable=False, default="")
    explanation: Mapped[str] = mapped_column(Text, nullable=False, default="")
    bloom_level: Mapped[str] = mapped_column(
        String(20), nullable=False, default="Understand"
    )
    difficulty: Mapped[str] = mapped_column(
        String(10), nullable=False, default="medium"
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class QuizAttemptModel(Base, UUIDMixin):
    __tablename__ = "quiz_attempts"

    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    quiz_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("quizzes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    correct_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_answered: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    total_time_ms: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )


class QuizResponseModel(Base, UUIDMixin):
    __tablename__ = "quiz_responses"
    __table_args__ = (UniqueConstraint("attempt_id", "question_id"),)

    attempt_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("quiz_attempts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    question_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("quiz_questions.id", ondelete="CASCADE"),
        nullable=False,
    )
    selected_answer: Mapped[str] = mapped_column(Text, nullable=False, default="")
    is_correct: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    time_spent_ms: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
