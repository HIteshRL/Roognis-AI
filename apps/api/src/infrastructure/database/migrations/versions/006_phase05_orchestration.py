"""Phase 0.5 — Learning Orchestration: intent on sessions, concept_memory table.

Revision ID: 006
Revises: 005
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add intent column to learning_sessions
    op.add_column(
        "learning_sessions",
        sa.Column("intent", sa.String(30), nullable=False, server_default="unknown"),
    )

    # Concept memory — per-concept teaching history per student
    op.create_table(
        "concept_memory",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("concept_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("concept_name", sa.String(200), nullable=False),
        sa.Column("times_taught", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("successful_approaches", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_approaches", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_approach", sa.String(30), nullable=True),
        sa.Column("teaching_notes", postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default="[]"),
        sa.Column("last_taught", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["concept_id"], ["concept_nodes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "concept_id"),
    )
    op.create_index("ix_concept_memory_user_id", "concept_memory", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_concept_memory_user_id", table_name="concept_memory")
    op.drop_table("concept_memory")
    op.drop_column("learning_sessions", "intent")
