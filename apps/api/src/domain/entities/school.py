from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4


class Role:
    STUDENT = "student"
    TEACHER = "teacher"
    SCHOOL_ADMIN = "school_admin"
    PARENT = "parent"

    STAFF = frozenset({TEACHER, SCHOOL_ADMIN})
    ALL = frozenset({STUDENT, TEACHER, SCHOOL_ADMIN, PARENT})


@dataclass
class School:
    name: str
    id: UUID = field(default_factory=uuid4)
    slug: str = ""
    address: str | None = None
    created_by: UUID | None = None
    is_active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class SchoolMember:
    school_id: UUID
    user_id: UUID
    id: UUID = field(default_factory=uuid4)
    role: str = Role.TEACHER
    status: str = "active"
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def is_school_admin(self) -> bool:
        return self.role == Role.SCHOOL_ADMIN


@dataclass
class Classroom:
    school_id: UUID
    name: str
    id: UUID = field(default_factory=uuid4)
    subject: str | None = None
    grade: str | None = None
    teacher_id: UUID | None = None
    join_code: str = ""
    description: str | None = None
    is_active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class Enrollment:
    classroom_id: UUID
    student_id: UUID
    id: UUID = field(default_factory=uuid4)
    status: str = "active"
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def is_active(self) -> bool:
        return self.status == "active"


@dataclass
class SyllabusItem:
    classroom_id: UUID
    subject: str
    chapter: str
    id: UUID = field(default_factory=uuid4)
    topic: str | None = None
    description: str | None = None
    order_index: int = 0
    knowledge_base_id: UUID | None = None
    is_published: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
