"""
Teacher persona domain entities (Google Classroom model).

Classroom  — a teacher-owned "subject"/class students join via a code.
Chapter    — an ordered unit within a classroom; its content lives in a
             KnowledgeBase (knowledge_base_id) so RAG scopes to it directly.
Enrollment — a student's membership in a classroom.

Pure Python, no I/O. Join-code generation lives here as domain logic.
"""
import secrets
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4

# Unambiguous alphabet — no O/0, I/1, so codes are easy to read out and type.
_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
_CODE_LENGTH = 6

# Google-Classroom-style header colours students recognise.
CLASSROOM_COLORS = [
    "#1967d2",  # blue
    "#1e8e3e",  # green
    "#e52592",  # pink
    "#9334e6",  # purple
    "#e8710a",  # orange
    "#00897b",  # teal
    "#d93025",  # red
    "#3949ab",  # indigo
]


def generate_join_code() -> str:
    """A short, unambiguous, uppercase join code (e.g. ``K7PQXR``)."""
    return "".join(secrets.choice(_CODE_ALPHABET) for _ in range(_CODE_LENGTH))


@dataclass
class Classroom:
    teacher_id: UUID
    name: str
    id: UUID = field(default_factory=uuid4)
    subject: str | None = None
    section: str | None = None
    room: str | None = None
    grade: str | None = None
    description: str | None = None
    color: str = CLASSROOM_COLORS[0]
    join_code: str = field(default_factory=generate_join_code)
    is_archived: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def archive(self) -> None:
        self.is_archived = True
        self.updated_at = datetime.now(UTC)

    def rotate_code(self) -> None:
        self.join_code = generate_join_code()
        self.updated_at = datetime.now(UTC)


@dataclass
class Chapter:
    classroom_id: UUID
    title: str
    id: UUID = field(default_factory=uuid4)
    knowledge_base_id: UUID | None = None
    description: str | None = None
    order_index: int = 0
    is_published: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class Enrollment:
    classroom_id: UUID
    student_id: UUID
    id: UUID = field(default_factory=uuid4)
    status: str = "active"
    joined_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
