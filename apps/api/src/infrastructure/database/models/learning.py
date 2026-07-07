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
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.database.base import Base, UUIDMixin


class StudentProfileModel(Base, UUIDMixin):
    __tablename__ = "student_profiles"

    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, unique=True, index=True,
    )
    institution: Mapped[str | None] = mapped_column(String(200), nullable=True)
    grade: Mapped[str | None] = mapped_column(String(100), nullable=True)
    subjects: Mapped[list] = mapped_column(JSONB, nullable=True, default=list)
    current_chapter: Mapped[str | None] = mapped_column(String(200), nullable=True)
    learning_velocity: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    behavioral_signals: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=dict)
    psychometric_profile: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=dict)
    last_active: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class LearningSessionModel(Base, UUIDMixin):
    __tablename__ = "learning_sessions"

    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    conversation_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)
    subject: Mapped[str | None] = mapped_column(String(200), nullable=True)
    chapter: Mapped[str | None] = mapped_column(String(200), nullable=True)
    grade: Mapped[str | None] = mapped_column(String(100), nullable=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    ai_response: Mapped[str] = mapped_column(Text, nullable=False)
    retrieved_context: Mapped[str | None] = mapped_column(Text, nullable=True)
    primary_concept: Mapped[str | None] = mapped_column(String(200), nullable=True)
    concepts_discussed: Mapped[list] = mapped_column(JSONB, nullable=True, default=list)
    skills: Mapped[list] = mapped_column(JSONB, nullable=True, default=list)
    bloom_level: Mapped[str] = mapped_column(String(20), nullable=False, default="Understand")
    difficulty_level: Mapped[str] = mapped_column(String(10), nullable=False, default="medium")
    misconceptions: Mapped[list] = mapped_column(JSONB, nullable=True, default=list)
    intent: Mapped[str] = mapped_column(String(30), nullable=False, default="unknown")
    token_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )


class ConceptNodeModel(Base, UUIDMixin):
    __tablename__ = "concept_nodes"

    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    subject: Mapped[str | None] = mapped_column(String(200), nullable=True)
    grade: Mapped[str | None] = mapped_column(String(100), nullable=True)
    chapter: Mapped[str | None] = mapped_column(String(200), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    bloom_level: Mapped[str] = mapped_column(String(20), nullable=False, default="Understand")
    difficulty: Mapped[str] = mapped_column(String(10), nullable=False, default="medium")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    prerequisites: Mapped[list["ConceptEdgeModel"]] = relationship(
        "ConceptEdgeModel",
        foreign_keys="ConceptEdgeModel.target_id",
        back_populates="target",
        cascade="all, delete-orphan",
    )
    successors: Mapped[list["ConceptEdgeModel"]] = relationship(
        "ConceptEdgeModel",
        foreign_keys="ConceptEdgeModel.source_id",
        back_populates="source",
        cascade="all, delete-orphan",
    )


class ConceptEdgeModel(Base, UUIDMixin):
    __tablename__ = "concept_edges"
    __table_args__ = (UniqueConstraint("source_id", "target_id"),)

    source_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("concept_nodes.id", ondelete="CASCADE"),
        nullable=False,
    )
    target_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("concept_nodes.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    weight: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    source: Mapped["ConceptNodeModel"] = relationship(
        "ConceptNodeModel", foreign_keys=[source_id], back_populates="successors"
    )
    target: Mapped["ConceptNodeModel"] = relationship(
        "ConceptNodeModel", foreign_keys=[target_id], back_populates="prerequisites"
    )


class MasteryRecordModel(Base, UUIDMixin):
    __tablename__ = "mastery_records"
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
    score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    interaction_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_updated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ConceptMemoryModel(Base, UUIDMixin):
    __tablename__ = "concept_memory"
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
    times_taught: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    successful_approaches: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_approaches: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_approach: Mapped[str | None] = mapped_column(String(30), nullable=True)
    teaching_notes: Mapped[list] = mapped_column(JSONB, nullable=True, default=list)
    last_taught: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class LearningGapModel(Base, UUIDMixin):
    __tablename__ = "learning_gaps"
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
    severity: Mapped[str] = mapped_column(String(10), nullable=False, default="medium")
    reason: Mapped[str] = mapped_column(Text, nullable=False, default="")
    confidence: Mapped[str] = mapped_column(String(10), nullable=False, default="medium")
    occurrence_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_resolved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
