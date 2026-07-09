"""Teacher content bridge — link a classroom to its knowledge base

Gives each classroom an optional owning knowledge base. Teacher-uploaded
materials ingest into this KB, and the student's AI tutor grounds its answers
in it (retrieval is scoped by knowledge_base_id). Nullable + SET NULL so the
column is fail-open: classrooms without uploads simply fall back to the
existing subject/chapter/grade retrieval.

Revision ID: 016
Revises: 015
Create Date: 2025-01-01 00:00:16.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "016"
down_revision: str | None = "015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "classrooms",
        sa.Column("knowledge_base_id", postgresql.UUID(as_uuid=False), nullable=True),
    )
    op.create_foreign_key(
        "fk_classrooms_knowledge_base_id",
        "classrooms",
        "knowledge_bases",
        ["knowledge_base_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_classrooms_knowledge_base_id", "classrooms", type_="foreignkey"
    )
    op.drop_column("classrooms", "knowledge_base_id")
