"""Cache & FAQ Intelligence — durable FAQ knowledge base

Backs the CachingEngine: hot queries (crossing a hit threshold) are promoted
into faq_entries for durability, analytics, and a public /faq endpoint. The
hot Redis cache itself needs no schema.

Revision ID: 012
Revises: 011
Create Date: 2025-01-01 00:00:11.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "012"
down_revision: str | None = "011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "faq_entries",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("cache_key", sa.String(80), nullable=False),
        sa.Column("normalized_query", sa.Text(), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("subject", sa.String(200), nullable=True),
        sa.Column("grade", sa.String(100), nullable=True),
        sa.Column("hit_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("source", sa.String(30), nullable=False, server_default="hot_query"),
        sa.Column(
            "last_hit_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("cache_key"),
    )
    op.create_index("ix_faq_entries_cache_key", "faq_entries", ["cache_key"])
    op.create_index("ix_faq_entries_subject", "faq_entries", ["subject"])
    op.create_index("ix_faq_entries_hit_count", "faq_entries", ["hit_count"])


def downgrade() -> None:
    op.drop_index("ix_faq_entries_hit_count", table_name="faq_entries")
    op.drop_index("ix_faq_entries_subject", table_name="faq_entries")
    op.drop_index("ix_faq_entries_cache_key", table_name="faq_entries")
    op.drop_table("faq_entries")
