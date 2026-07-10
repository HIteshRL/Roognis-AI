"""ORM models for the Learner Intelligence questioning + evidence subsystem.

Tables:
  learner_evidence     — append-only event store (event sourcing core)
  learner_questions    — generated adaptive questions + their lifecycle
  recall_schedules     — SM-2 spaced-repetition schedule per (user, concept)
  learner_preferences  — inferred learning-style preferences with confidence
"""
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
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base, UUIDMixin


class LearnerEvidenceModel(Base, UUIDMixin):
    __tablename__ = "learner_evidence"

    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    concept_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("concept_nodes.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )
    concept_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    signal: Mapped[str] = mapped_column(String(30), nullable=False)
    objective: Mapped[str] = mapped_column(String(30), nullable=False, default="verify_mastery")
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="question")
    weight: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    bloom_level: Mapped[str] = mapped_column(String(20), nullable=False, default="Understand")
    intent: Mapped[str] = mapped_column(String(30), nullable=False, default="unknown")
    question_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)
    confidence_before: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    confidence_after: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    detail: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )


class LearnerQuestionModel(Base, UUIDMixin):
    __tablename__ = "learner_questions"

    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    concept_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("concept_nodes.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    concept_name: Mapped[str] = mapped_column(String(200), nullable=False)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    objective: Mapped[str] = mapped_column(String(30), nullable=False, default="verify_mastery")
    purpose: Mapped[str] = mapped_column(Text, nullable=False, default="")
    difficulty: Mapped[str] = mapped_column(String(10), nullable=False, default="medium")
    bloom_level: Mapped[str] = mapped_column(String(20), nullable=False, default="Understand")
    expected_answer: Mapped[str] = mapped_column(Text, nullable=False, default="")
    confidence_threshold: Mapped[float] = mapped_column(Float, nullable=False, default=0.6)
    evidence_weight: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    status: Mapped[str] = mapped_column(String(15), nullable=False, default="pending", index=True)
    student_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_correct: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    feedback: Mapped[str] = mapped_column(Text, nullable=False, default="")
    scheduled_for: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    asked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    answered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class RecallScheduleModel(Base, UUIDMixin):
    __tablename__ = "recall_schedules"
    __table_args__ = (UniqueConstraint("user_id", "concept_id"),)

    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    concept_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("concept_nodes.id", ondelete="CASCADE"),
        nullable=False,
    )
    concept_name: Mapped[str] = mapped_column(String(200), nullable=False)
    interval_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ease_factor: Mapped[float] = mapped_column(Float, nullable=False, default=2.5)
    repetitions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    lapses: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    retention_probability: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    last_reviewed: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_review_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class LearnerPreferenceModel(Base, UUIDMixin):
    __tablename__ = "learner_preferences"
    __table_args__ = (UniqueConstraint("user_id", "dimension"),)

    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    dimension: Mapped[str] = mapped_column(String(30), nullable=False)
    strength: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    evidence_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_updated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
