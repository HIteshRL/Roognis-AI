"""curriculum rag — Phase 0.3

Adds academic hierarchy fields (grade, chapter, topic) to knowledge_bases.
Updates prompt templates to strict academic tutor versions.

Revision ID: 003
Revises: 002
Create Date: 2025-01-01 00:00:02.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "003"
down_revision: str | None = "002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("knowledge_bases", sa.Column("grade", sa.String(100), nullable=True))
    op.add_column("knowledge_bases", sa.Column("chapter", sa.String(200), nullable=True))
    op.add_column("knowledge_bases", sa.Column("topic", sa.String(200), nullable=True))

    op.create_index("ix_knowledge_bases_grade", "knowledge_bases", ["grade"])
    op.create_index("ix_knowledge_bases_subject", "knowledge_bases", ["subject"])

    # Replace Phase 0.2 prompts with strict academic tutor versions
    op.execute("""
        UPDATE prompt_templates
        SET template = 'You are an academic tutor for institutional curriculum.

Use ONLY the following curriculum excerpts to answer the student''s question:

{context}

Rules:
- Answer strictly from the provided context.
- If the answer is not present in the context above, respond EXACTLY with: "I cannot find this information in the provided curriculum."
- Never fabricate academic content, statistics, or explanations.
- Cite the source document and page number when available.
- Be precise, educational, and appropriate for the student''s grade level.',
            description = 'Strict academic tutor prompt — curriculum-bound answers only'
        WHERE name = 'rag_system';
    """)

    op.execute("""
        UPDATE prompt_templates
        SET template = 'You are an academic tutor for institutional curriculum.

No relevant curriculum content was found for this question in the knowledge base.

Respond EXACTLY with: "I cannot find this information in the provided curriculum."

Do not attempt to answer from general knowledge.',
            description = 'Strict no-context response — forces curriculum-only answer'
        WHERE name = 'rag_no_context';
    """)


def downgrade() -> None:
    op.drop_index("ix_knowledge_bases_subject", "knowledge_bases")
    op.drop_index("ix_knowledge_bases_grade", "knowledge_bases")
    op.drop_column("knowledge_bases", "topic")
    op.drop_column("knowledge_bases", "chapter")
    op.drop_column("knowledge_bases", "grade")
