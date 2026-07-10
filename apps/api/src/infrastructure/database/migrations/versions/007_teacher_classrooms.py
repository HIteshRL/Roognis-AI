"""Phase 0.6 — Teacher persona: role on users, classrooms, chapters, enrollments.

Google Classroom model: a teacher owns classrooms (their "subjects"), each
classroom has ordered chapters, each chapter wraps a knowledge_base for its
content, and students enrol into a classroom via its join code.

Revision ID: 007
Revises: 006
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Role on users ────────────────────────────────────────────────────────
    op.add_column(
        "users",
        sa.Column("role", sa.String(20), nullable=False, server_default="student"),
    )
    op.create_index("ix_users_role", "users", ["role"])

    # ── Classrooms (teacher-owned "subject" / Google Classroom class) ────────
    op.create_table(
        "classrooms",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("teacher_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("subject", sa.String(100), nullable=True),
        sa.Column("section", sa.String(100), nullable=True),
        sa.Column("room", sa.String(100), nullable=True),
        sa.Column("grade", sa.String(20), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("color", sa.String(20), nullable=False, server_default="#1967d2"),
        sa.Column("join_code", sa.String(12), nullable=False),
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["teacher_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("join_code"),
    )
    op.create_index("ix_classrooms_teacher_id", "classrooms", ["teacher_id"])
    op.create_index("ix_classrooms_join_code", "classrooms", ["join_code"])

    # ── Chapters (ordered units within a classroom, each wraps a KB) ─────────
    op.create_table(
        "chapters",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("classroom_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("knowledge_base_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_published", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["classroom_id"], ["classrooms.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["knowledge_base_id"], ["knowledge_bases.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_chapters_classroom_id", "chapters", ["classroom_id"])

    # ── Enrollments (student ↔ classroom) ────────────────────────────────────
    op.create_table(
        "enrollments",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("classroom_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("student_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("joined_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["classroom_id"], ["classrooms.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["student_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("classroom_id", "student_id"),
    )
    op.create_index("ix_enrollments_student_id", "enrollments", ["student_id"])
    op.create_index("ix_enrollments_classroom_id", "enrollments", ["classroom_id"])


def downgrade() -> None:
    op.drop_index("ix_enrollments_classroom_id", table_name="enrollments")
    op.drop_index("ix_enrollments_student_id", table_name="enrollments")
    op.drop_table("enrollments")

    op.drop_index("ix_chapters_classroom_id", table_name="chapters")
    op.drop_table("chapters")

    op.drop_index("ix_classrooms_join_code", table_name="classrooms")
    op.drop_index("ix_classrooms_teacher_id", table_name="classrooms")
    op.drop_table("classrooms")

    op.drop_index("ix_users_role", table_name="users")
    op.drop_column("users", "role")
