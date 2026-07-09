"""Phase 0.6 — Quiz & Assessment Engine

Four tables: quizzes, quiz_questions, quiz_attempts, quiz_responses.

Revision ID: 008
Revises: 007
Create Date: 2025-01-01 00:00:07.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "008"
down_revision: str | None = "007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "quizzes",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("subject", sa.String(200), nullable=True),
        sa.Column("chapter", sa.String(200), nullable=True),
        sa.Column("difficulty", sa.String(10), nullable=False, server_default="medium"),
        sa.Column("question_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("best_score", sa.Float(), nullable=False, server_default="0.0"),
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
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_quizzes_user_id", "quizzes", ["user_id"])
    op.create_index("ix_quizzes_created_at", "quizzes", ["created_at"])

    op.create_table(
        "quiz_questions",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("quiz_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("concept_name", sa.String(200), nullable=False),
        sa.Column("concept_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column(
            "question_type",
            sa.String(20),
            nullable=False,
            server_default="mcq",
        ),
        sa.Column("options", postgresql.JSONB(), nullable=True, server_default="[]"),
        sa.Column("correct_answer", sa.Text(), nullable=False, server_default=""),
        sa.Column("explanation", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "bloom_level", sa.String(20), nullable=False, server_default="Understand"
        ),
        sa.Column(
            "difficulty", sa.String(10), nullable=False, server_default="medium"
        ),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["quiz_id"], ["quizzes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_quiz_questions_quiz_id", "quiz_questions", ["quiz_id"])

    op.create_table(
        "quiz_attempts",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("quiz_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("correct_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_answered", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_time_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["quiz_id"], ["quizzes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_quiz_attempts_user_id", "quiz_attempts", ["user_id"])
    op.create_index("ix_quiz_attempts_quiz_id", "quiz_attempts", ["quiz_id"])
    op.create_index("ix_quiz_attempts_created_at", "quiz_attempts", ["created_at"])

    op.create_table(
        "quiz_responses",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("attempt_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("question_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("selected_answer", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "is_correct", sa.Boolean(), nullable=False, server_default="false"
        ),
        sa.Column(
            "time_spent_ms", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["attempt_id"], ["quiz_attempts.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["question_id"], ["quiz_questions.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("attempt_id", "question_id"),
    )
    op.create_index("ix_quiz_responses_attempt_id", "quiz_responses", ["attempt_id"])


def downgrade() -> None:
    op.drop_index("ix_quiz_responses_attempt_id", table_name="quiz_responses")
    op.drop_table("quiz_responses")

    op.drop_index("ix_quiz_attempts_created_at", table_name="quiz_attempts")
    op.drop_index("ix_quiz_attempts_quiz_id", table_name="quiz_attempts")
    op.drop_index("ix_quiz_attempts_user_id", table_name="quiz_attempts")
    op.drop_table("quiz_attempts")

    op.drop_index("ix_quiz_questions_quiz_id", table_name="quiz_questions")
    op.drop_table("quiz_questions")

    op.drop_index("ix_quizzes_created_at", table_name="quizzes")
    op.drop_index("ix_quizzes_user_id", table_name="quizzes")
    op.drop_table("quizzes")
