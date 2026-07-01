"""learning engine — Phase 0.4

Student profiles, session memory, concept graph, mastery records, learning gaps.

Revision ID: 004
Revises: 003
Create Date: 2025-01-01 00:00:03.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "004"
down_revision: str | None = "003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── student_profiles ──────────────────────────────────────────────────────
    op.create_table(
        "student_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("institution", sa.String(200), nullable=True),
        sa.Column("grade", sa.String(100), nullable=True),
        sa.Column("subjects", postgresql.JSONB(), nullable=True, server_default="[]"),
        sa.Column("current_chapter", sa.String(200), nullable=True),
        sa.Column("learning_velocity", sa.Float(), nullable=False, server_default="0"),
        sa.Column("confidence_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("last_active", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index("ix_student_profiles_user_id", "student_profiles", ["user_id"])

    # ── learning_sessions ─────────────────────────────────────────────────────
    op.create_table(
        "learning_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("subject", sa.String(200), nullable=True),
        sa.Column("chapter", sa.String(200), nullable=True),
        sa.Column("grade", sa.String(100), nullable=True),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("ai_response", sa.Text(), nullable=False),
        sa.Column("retrieved_context", sa.Text(), nullable=True),
        sa.Column("primary_concept", sa.String(200), nullable=True),
        sa.Column("concepts_discussed", postgresql.JSONB(), nullable=True, server_default="[]"),
        sa.Column("skills", postgresql.JSONB(), nullable=True, server_default="[]"),
        sa.Column("bloom_level", sa.String(20), nullable=False, server_default="Understand"),
        sa.Column("difficulty_level", sa.String(10), nullable=False, server_default="medium"),
        sa.Column("misconceptions", postgresql.JSONB(), nullable=True, server_default="[]"),
        sa.Column("token_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("duration_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_learning_sessions_user_id", "learning_sessions", ["user_id"])
    op.create_index("ix_learning_sessions_created_at", "learning_sessions", ["created_at"])

    # ── concept_nodes ─────────────────────────────────────────────────────────
    op.create_table(
        "concept_nodes",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("subject", sa.String(200), nullable=True),
        sa.Column("grade", sa.String(100), nullable=True),
        sa.Column("chapter", sa.String(200), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("bloom_level", sa.String(20), nullable=False, server_default="Understand"),
        sa.Column("difficulty", sa.String(10), nullable=False, server_default="medium"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_concept_nodes_name", "concept_nodes", ["name"])
    op.create_index("ix_concept_nodes_subject_grade", "concept_nodes", ["subject", "grade"])

    # ── concept_edges ─────────────────────────────────────────────────────────
    op.create_table(
        "concept_edges",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("target_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("weight", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["source_id"], ["concept_nodes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_id"], ["concept_nodes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_id", "target_id"),
    )
    op.create_index("ix_concept_edges_target_id", "concept_edges", ["target_id"])

    # ── mastery_records ───────────────────────────────────────────────────────
    op.create_table(
        "mastery_records",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("concept_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("concept_name", sa.String(200), nullable=False),
        sa.Column("score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("interaction_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_updated", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["concept_id"], ["concept_nodes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "concept_id"),
    )
    op.create_index("ix_mastery_records_user_id", "mastery_records", ["user_id"])

    # ── learning_gaps ─────────────────────────────────────────────────────────
    op.create_table(
        "learning_gaps",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("concept_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("concept_name", sa.String(200), nullable=False),
        sa.Column("severity", sa.String(10), nullable=False, server_default="medium"),
        sa.Column("reason", sa.Text(), nullable=False, server_default=""),
        sa.Column("confidence", sa.String(10), nullable=False, server_default="medium"),
        sa.Column("occurrence_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("is_resolved", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["concept_id"], ["concept_nodes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "concept_id"),
    )
    op.create_index("ix_learning_gaps_user_id", "learning_gaps", ["user_id"])
    op.create_index("ix_learning_gaps_severity", "learning_gaps", ["severity"])


def downgrade() -> None:
    op.drop_table("learning_gaps")
    op.drop_table("mastery_records")
    op.drop_table("concept_edges")
    op.drop_table("concept_nodes")
    op.drop_table("learning_sessions")
    op.drop_table("student_profiles")
