"""LMS core — Google Classroom parity layer.

Institutions, co-teaching, invitations, folders/materials (+versions),
coursework (+attachments), submissions (+attachments), grades, discussion
comments (+reactions), poll votes, notifications, bookmarks, material views,
auth tokens (password reset / email verification), and additive columns on
classrooms and users.

Revision ID: 009
Revises: 008
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Institutions ─────────────────────────────────────────────────────────
    op.create_table(
        "institutions",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("name", sa.String(300), nullable=False),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("contact_email", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_institutions_name", "institutions", ["name"])

    # ── Additive columns: users, classrooms ─────────────────────────────────
    op.add_column(
        "users",
        sa.Column("institution_id", postgresql.UUID(as_uuid=False), nullable=True),
    )
    op.create_foreign_key(
        "fk_users_institution", "users", "institutions", ["institution_id"], ["id"],
        ondelete="SET NULL",
    )

    op.add_column("classrooms", sa.Column("semester", sa.String(50), nullable=True))
    op.add_column(
        "classrooms",
        sa.Column("institution_id", postgresql.UUID(as_uuid=False), nullable=True),
    )
    op.create_foreign_key(
        "fk_classrooms_institution", "classrooms", "institutions",
        ["institution_id"], ["id"], ondelete="SET NULL",
    )
    op.add_column("classrooms", sa.Column("banner_url", sa.Text(), nullable=True))
    op.add_column(
        "classrooms",
        sa.Column("settings", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
    )
    op.add_column(
        "classrooms",
        sa.Column("join_code_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )
    op.add_column(
        "classrooms",
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column("classrooms", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))

    # ── Co-teachers ──────────────────────────────────────────────────────────
    op.create_table(
        "classroom_teachers",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("classroom_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("teacher_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("role", sa.String(20), nullable=False, server_default="co_teacher"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["classroom_id"], ["classrooms.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["teacher_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("classroom_id", "teacher_id"),
    )
    op.create_index("ix_classroom_teachers_classroom_id", "classroom_teachers", ["classroom_id"])
    op.create_index("ix_classroom_teachers_teacher_id", "classroom_teachers", ["teacher_id"])

    # ── Invitations ──────────────────────────────────────────────────────────
    op.create_table(
        "classroom_invitations",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("classroom_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("invited_by", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("role", sa.String(20), nullable=False, server_default="student"),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("token", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["classroom_id"], ["classrooms.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["invited_by"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token"),
    )
    op.create_index("ix_classroom_invitations_classroom_id", "classroom_invitations", ["classroom_id"])
    op.create_index("ix_classroom_invitations_email", "classroom_invitations", ["email"])
    op.create_index("ix_classroom_invitations_status", "classroom_invitations", ["status"])

    # ── Folders ──────────────────────────────────────────────────────────────
    op.create_table(
        "folders",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("classroom_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("parent_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("name", sa.String(300), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["classroom_id"], ["classrooms.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parent_id"], ["folders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_folders_classroom_id", "folders", ["classroom_id"])
    op.create_index("ix_folders_parent_id", "folders", ["parent_id"])

    # ── Materials & versions ─────────────────────────────────────────────────
    op.create_table(
        "materials",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("classroom_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("folder_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("uploaded_by", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.String(30), nullable=False, server_default="other"),
        sa.Column("filename", sa.String(500), nullable=True),
        sa.Column("file_type", sa.String(50), nullable=True),
        sa.Column("file_size", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("storage_path", sa.Text(), nullable=True),
        sa.Column("link_url", sa.Text(), nullable=True),
        sa.Column("document_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("download_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["classroom_id"], ["classrooms.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["folder_id"], ["folders.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["uploaded_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_materials_classroom_id", "materials", ["classroom_id"])
    op.create_index("ix_materials_folder_id", "materials", ["folder_id"])
    op.create_index("ix_materials_category", "materials", ["category"])
    op.create_index("ix_materials_classroom_deleted", "materials", ["classroom_id", "is_deleted"])

    op.create_table(
        "material_versions",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("material_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("filename", sa.String(500), nullable=True),
        sa.Column("file_size", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("storage_path", sa.Text(), nullable=True),
        sa.Column("uploaded_by", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["material_id"], ["materials.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["uploaded_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("material_id", "version"),
    )
    op.create_index("ix_material_versions_material_id", "material_versions", ["material_id"])

    # ── Coursework & attachments ─────────────────────────────────────────────
    op.create_table(
        "coursework",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("classroom_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("author_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("type", sa.String(20), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("allow_late", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("max_marks", sa.Float(), nullable=True),
        sa.Column("rubric", postgresql.JSONB(), nullable=True),
        sa.Column("questions", postgresql.JSONB(), nullable=True),
        sa.Column("poll_options", postgresql.JSONB(), nullable=True),
        sa.Column("settings", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["classroom_id"], ["classrooms.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_coursework_classroom_id", "coursework", ["classroom_id"])
    op.create_index("ix_coursework_classroom_status", "coursework", ["classroom_id", "status"])
    op.create_index("ix_coursework_classroom_type", "coursework", ["classroom_id", "type"])

    op.create_table(
        "coursework_attachments",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("coursework_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("material_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("link_url", sa.Text(), nullable=True),
        sa.Column("title", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["coursework_id"], ["coursework.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["material_id"], ["materials.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_coursework_attachments_coursework_id", "coursework_attachments", ["coursework_id"])

    # ── Submissions, attachments, grades ─────────────────────────────────────
    op.create_table(
        "submissions",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("coursework_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("student_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("text_answer", sa.Text(), nullable=True),
        sa.Column("attempt", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("is_late", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["coursework_id"], ["coursework.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["student_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("coursework_id", "student_id"),
    )
    op.create_index("ix_submissions_coursework_id", "submissions", ["coursework_id"])
    op.create_index("ix_submissions_student_id", "submissions", ["student_id"])
    op.create_index("ix_submissions_status", "submissions", ["status"])

    op.create_table(
        "submission_attachments",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("submission_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("filename", sa.String(500), nullable=False),
        sa.Column("file_type", sa.String(50), nullable=True),
        sa.Column("file_size", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("storage_path", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["submission_id"], ["submissions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_submission_attachments_submission_id", "submission_attachments", ["submission_id"])

    op.create_table(
        "grades",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("submission_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("grader_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("max_marks", sa.Float(), nullable=True),
        sa.Column("rubric_scores", postgresql.JSONB(), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("private_feedback", sa.Text(), nullable=True),
        sa.Column("is_returned", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_regrade", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["submission_id"], ["submissions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["grader_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_grades_submission_id", "grades", ["submission_id"])

    # ── Discussion comments & reactions ──────────────────────────────────────
    op.create_table(
        "comments",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("classroom_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("coursework_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("parent_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("author_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("mentions", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["classroom_id"], ["classrooms.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["coursework_id"], ["coursework.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parent_id"], ["comments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_comments_classroom_id", "comments", ["classroom_id"])
    op.create_index("ix_comments_coursework_id", "comments", ["coursework_id"])
    op.create_index("ix_comments_parent_id", "comments", ["parent_id"])

    op.create_table(
        "comment_reactions",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("comment_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("emoji", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["comment_id"], ["comments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("comment_id", "user_id", "emoji"),
    )
    op.create_index("ix_comment_reactions_comment_id", "comment_reactions", ["comment_id"])

    # ── Poll votes ───────────────────────────────────────────────────────────
    op.create_table(
        "poll_votes",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("coursework_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("option_index", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["coursework_id"], ["coursework.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("coursework_id", "user_id"),
    )
    op.create_index("ix_poll_votes_coursework_id", "poll_votes", ["coursework_id"])

    # ── Notifications ────────────────────────────────────────────────────────
    op.create_table(
        "notifications",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("type", sa.String(40), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("body", sa.Text(), nullable=False, server_default=""),
        sa.Column("data", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])
    op.create_index("ix_notifications_user_read", "notifications", ["user_id", "is_read"])
    op.create_index("ix_notifications_user_created", "notifications", ["user_id", "created_at"])

    # ── Bookmarks & material views ───────────────────────────────────────────
    op.create_table(
        "bookmarks",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("material_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["material_id"], ["materials.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "material_id"),
    )
    op.create_index("ix_bookmarks_user_id", "bookmarks", ["user_id"])

    op.create_table(
        "material_views",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("material_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("view_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("progress", sa.Float(), nullable=False, server_default="0"),
        sa.Column("last_viewed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["material_id"], ["materials.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "material_id"),
    )
    op.create_index("ix_material_views_user_id", "material_views", ["user_id"])

    # ── Auth tokens (password reset / email verification) ────────────────────
    op.create_table(
        "auth_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("token_hash", sa.String(128), nullable=False),
        sa.Column("purpose", sa.String(30), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index("ix_auth_tokens_user_id", "auth_tokens", ["user_id"])

    # Backfill: every existing classroom owner becomes an explicit owner row.
    op.execute(
        """
        INSERT INTO classroom_teachers (id, classroom_id, teacher_id, role, created_at, updated_at)
        SELECT gen_random_uuid(), c.id, c.teacher_id, 'owner', now(), now()
        FROM classrooms c
        ON CONFLICT DO NOTHING
        """
    )


def downgrade() -> None:
    op.drop_table("auth_tokens")
    op.drop_table("material_views")
    op.drop_table("bookmarks")
    op.drop_table("notifications")
    op.drop_table("poll_votes")
    op.drop_table("comment_reactions")
    op.drop_table("comments")
    op.drop_table("grades")
    op.drop_table("submission_attachments")
    op.drop_table("submissions")
    op.drop_table("coursework_attachments")
    op.drop_table("coursework")
    op.drop_table("material_versions")
    op.drop_table("materials")
    op.drop_table("folders")
    op.drop_table("classroom_invitations")
    op.drop_table("classroom_teachers")
    op.drop_column("classrooms", "deleted_at")
    op.drop_column("classrooms", "is_deleted")
    op.drop_column("classrooms", "join_code_enabled")
    op.drop_column("classrooms", "settings")
    op.drop_column("classrooms", "banner_url")
    op.drop_constraint("fk_classrooms_institution", "classrooms", type_="foreignkey")
    op.drop_column("classrooms", "institution_id")
    op.drop_column("classrooms", "semester")
    op.drop_constraint("fk_users_institution", "users", type_="foreignkey")
    op.drop_column("users", "institution_id")
    op.drop_table("institutions")
