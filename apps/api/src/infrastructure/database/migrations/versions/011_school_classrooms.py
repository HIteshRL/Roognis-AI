"""Phase 0.8 — School / Teacher B2B2C backbone

Adds users.role and five tables: schools, school_members, classrooms,
enrollments, syllabus_items. Syllabus items optionally link to knowledge_bases
(reusing the document-ingestion pipeline for uploaded curriculum).

Revision ID: 011
Revises: 010
Create Date: 2025-01-01 00:00:10.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "011"
down_revision: str | None = "010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("role", sa.String(20), nullable=False, server_default="student"),
    )
    op.create_index("ix_users_role", "users", ["role"])

    op.create_table(
        "schools",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("slug", sa.String(120), nullable=False),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("ix_schools_slug", "schools", ["slug"])

    op.create_table(
        "school_members",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("school_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("role", sa.String(20), nullable=False, server_default="teacher"),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("school_id", "user_id"),
    )
    op.create_index("ix_school_members_school_id", "school_members", ["school_id"])
    op.create_index("ix_school_members_user_id", "school_members", ["user_id"])

    op.create_table(
        "classrooms",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("school_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("subject", sa.String(200), nullable=True),
        sa.Column("grade", sa.String(100), nullable=True),
        sa.Column("teacher_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("join_code", sa.String(16), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["teacher_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("join_code"),
    )
    op.create_index("ix_classrooms_school_id", "classrooms", ["school_id"])
    op.create_index("ix_classrooms_teacher_id", "classrooms", ["teacher_id"])
    op.create_index("ix_classrooms_join_code", "classrooms", ["join_code"])

    op.create_table(
        "enrollments",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("classroom_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("student_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["classroom_id"], ["classrooms.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["student_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("classroom_id", "student_id"),
    )
    op.create_index("ix_enrollments_classroom_id", "enrollments", ["classroom_id"])
    op.create_index("ix_enrollments_student_id", "enrollments", ["student_id"])

    op.create_table(
        "syllabus_items",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("classroom_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("subject", sa.String(200), nullable=False),
        sa.Column("chapter", sa.String(200), nullable=False),
        sa.Column("topic", sa.String(200), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("knowledge_base_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("is_published", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["classroom_id"], ["classrooms.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["knowledge_base_id"], ["knowledge_bases.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_syllabus_items_classroom_id", "syllabus_items", ["classroom_id"])


def downgrade() -> None:
    op.drop_index("ix_syllabus_items_classroom_id", table_name="syllabus_items")
    op.drop_table("syllabus_items")
    op.drop_index("ix_enrollments_student_id", table_name="enrollments")
    op.drop_index("ix_enrollments_classroom_id", table_name="enrollments")
    op.drop_table("enrollments")
    op.drop_index("ix_classrooms_join_code", table_name="classrooms")
    op.drop_index("ix_classrooms_teacher_id", table_name="classrooms")
    op.drop_index("ix_classrooms_school_id", table_name="classrooms")
    op.drop_table("classrooms")
    op.drop_index("ix_school_members_user_id", table_name="school_members")
    op.drop_index("ix_school_members_school_id", table_name="school_members")
    op.drop_table("school_members")
    op.drop_index("ix_schools_slug", table_name="schools")
    op.drop_table("schools")
    op.drop_index("ix_users_role", table_name="users")
    op.drop_column("users", "role")
