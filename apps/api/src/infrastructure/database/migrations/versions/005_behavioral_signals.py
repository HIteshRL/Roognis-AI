"""add behavioral_signals JSONB column to student_profiles

Phase 0.3 fix: computed behavioral intelligence derived from session history.

Revision ID: 005
Revises: 004
Create Date: 2025-01-01 00:00:04.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "005"
down_revision: str | None = "004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "student_profiles",
        sa.Column("behavioral_signals", postgresql.JSONB(), nullable=True, server_default="{}"),
    )


def downgrade() -> None:
    op.drop_column("student_profiles", "behavioral_signals")
