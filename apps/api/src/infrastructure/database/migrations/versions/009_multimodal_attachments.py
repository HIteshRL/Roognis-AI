"""Phase 0.7 — Multimodal Intelligence

One table: message_attachments (images attached to chat messages).

Revision ID: 009
Revises: 008
Create Date: 2025-01-01 00:00:08.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "009"
down_revision: str | None = "008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "message_attachments",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("message_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("kind", sa.String(20), nullable=False, server_default="image"),
        sa.Column("storage_path", sa.Text(), nullable=False),
        sa.Column("content_type", sa.String(100), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["message_id"], ["messages.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_message_attachments_user_id", "message_attachments", ["user_id"]
    )
    op.create_index(
        "ix_message_attachments_message_id", "message_attachments", ["message_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_message_attachments_message_id", table_name="message_attachments")
    op.drop_index("ix_message_attachments_user_id", table_name="message_attachments")
    op.drop_table("message_attachments")
