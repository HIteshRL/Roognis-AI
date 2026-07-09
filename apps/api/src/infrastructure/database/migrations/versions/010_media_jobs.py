"""v0.71 — Generative Multimodal Tutoring

One table: media_jobs (async video-generation jobs). Generated media reuses the
message_attachments table from migration 009 (no schema change needed there).

Revision ID: 010
Revises: 009
Create Date: 2025-01-01 00:00:09.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "010"
down_revision: str | None = "009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "media_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("message_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False, server_default="video"),
        sa.Column("status", sa.String(20), nullable=False, server_default="queued"),
        sa.Column("prompt", sa.Text(), nullable=False, server_default=""),
        sa.Column("attachment_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("progress", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["message_id"], ["messages.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["attachment_id"], ["message_attachments.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_media_jobs_user_id", "media_jobs", ["user_id"])
    op.create_index("ix_media_jobs_message_id", "media_jobs", ["message_id"])
    op.create_index("ix_media_jobs_status", "media_jobs", ["status"])


def downgrade() -> None:
    op.drop_index("ix_media_jobs_status", table_name="media_jobs")
    op.drop_index("ix_media_jobs_message_id", table_name="media_jobs")
    op.drop_index("ix_media_jobs_user_id", table_name="media_jobs")
    op.drop_table("media_jobs")
