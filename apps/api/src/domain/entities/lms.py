"""
LMS domain entities (Google Classroom parity layer).

Pure Python, no I/O. These extend the Phase-0.7 classroom model with
institutions, co-teaching, invitations, materials, coursework, submissions,
grading, discussions, notifications, and per-student material state.
"""
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4

# ── Enumerated string values (kept as constants — DB stores plain strings) ───

COURSEWORK_TYPES = (
    "announcement",
    "assignment",
    "homework",
    "quiz",
    "exam",
    "practice_set",
    "discussion",
    "poll",
)
COURSEWORK_STATUSES = ("draft", "scheduled", "published", "archived")
MATERIAL_CATEGORIES = (
    "note",
    "assignment",
    "reference",
    "question_paper",
    "solution",
    "other",
)
SUBMISSION_STATUSES = ("draft", "submitted", "returned", "withdrawn")
INVITATION_ROLES = ("student", "co_teacher")
INVITATION_STATUSES = ("pending", "accepted", "rejected", "revoked")
ENROLLMENT_STATUSES = ("pending", "active", "removed")
AUTH_TOKEN_PURPOSES = ("password_reset", "email_verify")


def _now() -> datetime:
    return datetime.now(UTC)


@dataclass
class Institution:
    name: str
    id: UUID = field(default_factory=uuid4)
    address: str | None = None
    contact_email: str | None = None
    is_active: bool = True
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)


@dataclass
class ClassroomTeacher:
    classroom_id: UUID
    teacher_id: UUID
    id: UUID = field(default_factory=uuid4)
    role: str = "co_teacher"  # "owner" | "co_teacher"
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)


@dataclass
class ClassroomInvitation:
    classroom_id: UUID
    email: str
    invited_by: UUID
    id: UUID = field(default_factory=uuid4)
    role: str = "student"
    status: str = "pending"
    token: str = ""
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)

    @property
    def is_pending(self) -> bool:
        return self.status == "pending"


@dataclass
class Folder:
    classroom_id: UUID
    name: str
    id: UUID = field(default_factory=uuid4)
    parent_id: UUID | None = None
    is_deleted: bool = False
    deleted_at: datetime | None = None
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)


@dataclass
class Material:
    classroom_id: UUID
    uploaded_by: UUID
    title: str
    id: UUID = field(default_factory=uuid4)
    folder_id: UUID | None = None
    description: str | None = None
    category: str = "other"
    filename: str | None = None
    file_type: str | None = None
    file_size: int = 0
    storage_path: str | None = None
    link_url: str | None = None
    document_id: UUID | None = None
    version: int = 1
    download_count: int = 0
    is_deleted: bool = False
    deleted_at: datetime | None = None
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)

    def soft_delete(self) -> None:
        self.is_deleted = True
        self.deleted_at = _now()

    def restore(self) -> None:
        self.is_deleted = False
        self.deleted_at = None


@dataclass
class MaterialVersion:
    material_id: UUID
    version: int
    id: UUID = field(default_factory=uuid4)
    filename: str | None = None
    file_size: int = 0
    storage_path: str | None = None
    uploaded_by: UUID | None = None
    created_at: datetime = field(default_factory=_now)


@dataclass
class Coursework:
    classroom_id: UUID
    author_id: UUID
    type: str
    title: str
    id: UUID = field(default_factory=uuid4)
    body: str | None = None
    status: str = "draft"
    scheduled_at: datetime | None = None
    published_at: datetime | None = None
    due_at: datetime | None = None
    allow_late: bool = True
    max_marks: float | None = None
    rubric: list | None = None  # [{criterion, description, max_points}]
    questions: list | None = None  # quiz/exam/practice_set question payloads
    poll_options: list | None = None  # ["option a", "option b", ...]
    settings: dict = field(default_factory=dict)
    version: int = 1  # optimistic-locking token
    is_deleted: bool = False
    deleted_at: datetime | None = None
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)

    @property
    def is_visible_to_students(self) -> bool:
        return self.status == "published" and not self.is_deleted

    def publish(self) -> None:
        self.status = "published"
        self.published_at = _now()
        self.scheduled_at = None

    def accepts_submissions_at(self, at: datetime) -> bool:
        if not self.is_visible_to_students:
            return False
        if self.due_at and at > self.due_at:
            return self.allow_late
        return True

    def is_late_at(self, at: datetime) -> bool:
        return bool(self.due_at and at > self.due_at)


@dataclass
class CourseworkAttachment:
    coursework_id: UUID
    id: UUID = field(default_factory=uuid4)
    material_id: UUID | None = None
    link_url: str | None = None
    title: str | None = None
    created_at: datetime = field(default_factory=_now)


@dataclass
class Submission:
    coursework_id: UUID
    student_id: UUID
    id: UUID = field(default_factory=uuid4)
    status: str = "draft"
    text_answer: str | None = None
    attempt: int = 1
    is_late: bool = False
    submitted_at: datetime | None = None
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)

    @property
    def is_submitted(self) -> bool:
        return self.status == "submitted"


@dataclass
class SubmissionAttachment:
    submission_id: UUID
    filename: str
    id: UUID = field(default_factory=uuid4)
    file_type: str | None = None
    file_size: int = 0
    storage_path: str = ""
    created_at: datetime = field(default_factory=_now)


@dataclass
class Grade:
    submission_id: UUID
    score: float
    id: UUID = field(default_factory=uuid4)
    grader_id: UUID | None = None
    max_marks: float | None = None
    rubric_scores: list | None = None  # [{criterion, points}]
    comment: str | None = None
    private_feedback: str | None = None
    is_returned: bool = False
    is_regrade: bool = False
    created_at: datetime = field(default_factory=_now)


@dataclass
class Comment:
    classroom_id: UUID
    author_id: UUID
    body: str
    id: UUID = field(default_factory=uuid4)
    coursework_id: UUID | None = None
    parent_id: UUID | None = None
    mentions: list = field(default_factory=list)  # user id strings
    is_deleted: bool = False
    deleted_at: datetime | None = None
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)


@dataclass
class CommentReaction:
    comment_id: UUID
    user_id: UUID
    emoji: str
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=_now)


@dataclass
class PollVote:
    coursework_id: UUID
    user_id: UUID
    option_index: int
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=_now)


@dataclass
class Notification:
    user_id: UUID
    type: str
    title: str
    id: UUID = field(default_factory=uuid4)
    body: str = ""
    data: dict = field(default_factory=dict)
    is_read: bool = False
    created_at: datetime = field(default_factory=_now)


@dataclass
class Bookmark:
    user_id: UUID
    material_id: UUID
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=_now)


@dataclass
class MaterialView:
    user_id: UUID
    material_id: UUID
    id: UUID = field(default_factory=uuid4)
    view_count: int = 1
    progress: float = 0.0  # 0..1 — powers "continue reading"
    last_viewed_at: datetime = field(default_factory=_now)


@dataclass
class AuthToken:
    user_id: UUID
    token_hash: str
    purpose: str
    expires_at: datetime
    id: UUID = field(default_factory=uuid4)
    used_at: datetime | None = None
    created_at: datetime = field(default_factory=_now)

    def is_valid_at(self, at: datetime) -> bool:
        return self.used_at is None and at < self.expires_at
