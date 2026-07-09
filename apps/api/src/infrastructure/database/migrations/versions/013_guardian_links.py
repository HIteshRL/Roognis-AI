"""Parent Portal — guardian links (ADR-013)

A consent-based link between a parent user and a student user. The ephemeral
link code lives in Redis (TTL); this table holds the durable relationship.

Revision ID: 013
Revises: 012
Create Date: 2025-01-01 00:00:12.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "013"
down_revision: str | None = "012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "guardian_links",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("parent_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("student_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["parent_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["student_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("parent_id", "student_id"),
    )
    op.create_index("ix_guardian_links_parent_id", "guardian_links", ["parent_id"])
    op.create_index("ix_guardian_links_student_id", "guardian_links", ["student_id"])


def downgrade() -> None:
    op.drop_index("ix_guardian_links_student_id", table_name="guardian_links")
    op.drop_index("ix_guardian_links_parent_id", table_name="guardian_links")
    op.drop_table("guardian_links")
