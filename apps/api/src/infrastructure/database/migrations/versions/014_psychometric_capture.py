"""Phase A — psychometric capture

Adds a measured psychographic profile (JSONB) to student_profiles and a
per-question response log. Mirrors the migration 005 pattern for the JSONB
column (nullable + server_default '{}').

Revision ID: 014
Revises: 013
Create Date: 2025-01-01 00:00:13.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "014"
down_revision: str | None = "013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "student_profiles",
        sa.Column("psychometric_profile", postgresql.JSONB(), nullable=True, server_default="{}"),
    )
    op.create_table(
        "psychometric_responses",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("question_key", sa.String(60), nullable=False),
        sa.Column("question_text", sa.Text(), nullable=True),
        sa.Column("dimension", sa.String(30), nullable=False),
        sa.Column("response_value", sa.String(60), nullable=False),
        sa.Column("response_raw", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "question_key"),
    )
    op.create_index(
        "ix_psychometric_responses_user_id", "psychometric_responses", ["user_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_psychometric_responses_user_id", table_name="psychometric_responses")
    op.drop_table("psychometric_responses")
    op.drop_column("student_profiles", "psychometric_profile")
