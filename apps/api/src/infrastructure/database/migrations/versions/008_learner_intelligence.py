"""Learner Intelligence — evidence-driven questioning subsystem.

Adds the event-sourced evidence store, generated-question lifecycle table,
SM-2 recall schedules, and inferred learning-style preferences.

Revision ID: 008
Revises: 007
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Append-only evidence event store ────────────────────────────────────
    op.create_table(
        "learner_evidence",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("concept_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("concept_name", sa.String(200), nullable=True),
        sa.Column("signal", sa.String(30), nullable=False),
        sa.Column("objective", sa.String(30), nullable=False, server_default="verify_mastery"),
        sa.Column("source", sa.String(20), nullable=False, server_default="question"),
        sa.Column("weight", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("bloom_level", sa.String(20), nullable=False, server_default="Understand"),
        sa.Column("intent", sa.String(30), nullable=False, server_default="unknown"),
        sa.Column("question_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("confidence_before", sa.Float(), nullable=False, server_default="0"),
        sa.Column("confidence_after", sa.Float(), nullable=False, server_default="0"),
        sa.Column("detail", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["concept_id"], ["concept_nodes.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_learner_evidence_user_id", "learner_evidence", ["user_id"])
    op.create_index("ix_learner_evidence_concept_id", "learner_evidence", ["concept_id"])
    op.create_index("ix_learner_evidence_created_at", "learner_evidence", ["created_at"])

    # ── Generated adaptive questions + lifecycle ────────────────────────────
    op.create_table(
        "learner_questions",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("concept_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("concept_name", sa.String(200), nullable=False),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column("objective", sa.String(30), nullable=False, server_default="verify_mastery"),
        sa.Column("purpose", sa.Text(), nullable=False, server_default=""),
        sa.Column("difficulty", sa.String(10), nullable=False, server_default="medium"),
        sa.Column("bloom_level", sa.String(20), nullable=False, server_default="Understand"),
        sa.Column("expected_answer", sa.Text(), nullable=False, server_default=""),
        sa.Column("confidence_threshold", sa.Float(), nullable=False, server_default="0.6"),
        sa.Column("evidence_weight", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("status", sa.String(15), nullable=False, server_default="pending"),
        sa.Column("student_answer", sa.Text(), nullable=True),
        sa.Column("is_correct", sa.Boolean(), nullable=True),
        sa.Column("score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("feedback", sa.Text(), nullable=False, server_default=""),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=True),
        sa.Column("asked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("answered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["concept_id"], ["concept_nodes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_learner_questions_user_id", "learner_questions", ["user_id"])
    op.create_index("ix_learner_questions_concept_id", "learner_questions", ["concept_id"])
    op.create_index("ix_learner_questions_status", "learner_questions", ["status"])
    op.create_index("ix_learner_questions_created_at", "learner_questions", ["created_at"])

    # ── SM-2 recall schedules ───────────────────────────────────────────────
    op.create_table(
        "recall_schedules",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("concept_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("concept_name", sa.String(200), nullable=False),
        sa.Column("interval_days", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ease_factor", sa.Float(), nullable=False, server_default="2.5"),
        sa.Column("repetitions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("lapses", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("retention_probability", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("last_reviewed", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_review_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["concept_id"], ["concept_nodes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "concept_id"),
    )
    op.create_index("ix_recall_schedules_user_id", "recall_schedules", ["user_id"])
    op.create_index("ix_recall_schedules_next_review_at", "recall_schedules", ["next_review_at"])

    # ── Inferred learning-style preferences ─────────────────────────────────
    op.create_table(
        "learner_preferences",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("dimension", sa.String(30), nullable=False),
        sa.Column("strength", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0"),
        sa.Column("evidence_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_updated", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "dimension"),
    )
    op.create_index("ix_learner_preferences_user_id", "learner_preferences", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_learner_preferences_user_id", table_name="learner_preferences")
    op.drop_table("learner_preferences")

    op.drop_index("ix_recall_schedules_next_review_at", table_name="recall_schedules")
    op.drop_index("ix_recall_schedules_user_id", table_name="recall_schedules")
    op.drop_table("recall_schedules")

    op.drop_index("ix_learner_questions_created_at", table_name="learner_questions")
    op.drop_index("ix_learner_questions_status", table_name="learner_questions")
    op.drop_index("ix_learner_questions_concept_id", table_name="learner_questions")
    op.drop_index("ix_learner_questions_user_id", table_name="learner_questions")
    op.drop_table("learner_questions")

    op.drop_index("ix_learner_evidence_created_at", table_name="learner_evidence")
    op.drop_index("ix_learner_evidence_concept_id", table_name="learner_evidence")
    op.drop_index("ix_learner_evidence_user_id", table_name="learner_evidence")
    op.drop_table("learner_evidence")
