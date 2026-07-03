"""add subject and chapter columns to conversations

Scopes conversations by subject/chapter to prevent context rot and
enable subject-level organization in the chat sidebar.

Revision ID: 007
Revises: 006
Create Date: 2025-01-01 00:00:06.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "007"
down_revision: str | None = "006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "conversations",
        sa.Column("subject", sa.String(200), nullable=True),
    )
    op.add_column(
        "conversations",
        sa.Column("chapter", sa.String(200), nullable=True),
    )
    op.create_index("ix_conversations_subject", "conversations", ["subject"])


def downgrade() -> None:
    op.drop_index("ix_conversations_subject", table_name="conversations")
    op.drop_column("conversations", "chapter")
    op.drop_column("conversations", "subject")
