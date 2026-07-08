"""Phase B — persistent question bank + Elo ability rating

Adds a reusable, self-calibrating question bank; a per-(user, concept) Elo
ability rating alongside the existing mastery score (both coexist — build on
top, do not replace); and a provenance link from a served quiz question back
to its bank item.

Revision ID: 015
Revises: 014
Create Date: 2025-01-01 00:00:14.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "015"
down_revision: str | None = "014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "question_bank",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("concept_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("concept_name", sa.String(200), nullable=False),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column("question_type", sa.String(20), nullable=False, server_default="mcq"),
        sa.Column("options", postgresql.JSONB(), nullable=True),
        sa.Column("correct_answer", sa.Text(), nullable=False, server_default=""),
        sa.Column("explanation", sa.Text(), nullable=False, server_default=""),
        sa.Column("bloom_level", sa.String(20), nullable=False, server_default="Understand"),
        sa.Column("difficulty", sa.String(10), nullable=False, server_default="medium"),
        sa.Column("difficulty_rating", sa.Float(), nullable=False, server_default="1200"),
        sa.Column("times_served", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("times_correct", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("source", sa.String(20), nullable=False, server_default="llm"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["concept_id"], ["concept_nodes.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_question_bank_concept_id", "question_bank", ["concept_id"]
    )
    op.create_index(
        "ix_question_bank_concept_diff",
        "question_bank",
        ["concept_id", "difficulty_rating"],
    )

    op.add_column(
        "mastery_records",
        sa.Column("ability_rating", sa.Float(), nullable=True),
    )
    op.add_column(
        "quiz_questions",
        sa.Column("bank_question_id", postgresql.UUID(as_uuid=False), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("quiz_questions", "bank_question_id")
    op.drop_column("mastery_records", "ability_rating")
    op.drop_index("ix_question_bank_concept_diff", table_name="question_bank")
    op.drop_index("ix_question_bank_concept_id", table_name="question_bank")
    op.drop_table("question_bank")
