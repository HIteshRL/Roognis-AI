from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base, TimestampMixin, UUIDMixin


class SchoolModel(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "schools"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class SchoolMemberModel(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "school_members"
    __table_args__ = (UniqueConstraint("school_id", "user_id"),)

    school_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("schools.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="teacher")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")


class ClassroomModel(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "classrooms"

    school_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("schools.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    subject: Mapped[str | None] = mapped_column(String(200), nullable=True)
    grade: Mapped[str | None] = mapped_column(String(100), nullable=True)
    teacher_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )
    join_code: Mapped[str] = mapped_column(String(16), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    knowledge_base_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("knowledge_bases.id", ondelete="SET NULL"),
        nullable=True,
    )


class EnrollmentModel(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "enrollments"
    __table_args__ = (UniqueConstraint("classroom_id", "student_id"),)

    classroom_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("classrooms.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    student_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")


class SyllabusItemModel(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "syllabus_items"

    classroom_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("classrooms.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    subject: Mapped[str] = mapped_column(String(200), nullable=False)
    chapter: Mapped[str] = mapped_column(String(200), nullable=False)
    topic: Mapped[str | None] = mapped_column(String(200), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    knowledge_base_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("knowledge_bases.id", ondelete="SET NULL"),
        nullable=True,
    )
    is_published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
