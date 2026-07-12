"""Abstract repositories for the LMS (Google Classroom parity) layer."""
from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID

from src.domain.entities.lms import (
    AuthToken,
    Bookmark,
    ClassroomInvitation,
    ClassroomTeacher,
    Comment,
    CommentReaction,
    Coursework,
    CourseworkAttachment,
    Folder,
    Grade,
    Institution,
    Material,
    MaterialVersion,
    MaterialView,
    Notification,
    PollVote,
    Submission,
    SubmissionAttachment,
)
from src.domain.entities.user import User


class AbstractInstitutionRepository(ABC):
    @abstractmethod
    async def create(self, institution: Institution) -> Institution: ...

    @abstractmethod
    async def get_by_id(self, institution_id: UUID) -> Institution | None: ...

    @abstractmethod
    async def list(
        self, page: int = 1, limit: int = 20, search: str | None = None
    ) -> tuple[list[Institution], int]: ...

    @abstractmethod
    async def update(self, institution: Institution) -> Institution: ...

    @abstractmethod
    async def delete(self, institution_id: UUID) -> None: ...


class AbstractClassroomTeacherRepository(ABC):
    @abstractmethod
    async def add(self, membership: ClassroomTeacher) -> ClassroomTeacher: ...

    @abstractmethod
    async def get(self, classroom_id: UUID, teacher_id: UUID) -> ClassroomTeacher | None: ...

    @abstractmethod
    async def list_by_classroom(self, classroom_id: UUID) -> list[ClassroomTeacher]: ...

    @abstractmethod
    async def list_classroom_ids_for_teacher(self, teacher_id: UUID) -> list[UUID]: ...

    @abstractmethod
    async def remove(self, classroom_id: UUID, teacher_id: UUID) -> None: ...


class AbstractInvitationRepository(ABC):
    @abstractmethod
    async def create(self, invitation: ClassroomInvitation) -> ClassroomInvitation: ...

    @abstractmethod
    async def get_by_id(self, invitation_id: UUID) -> ClassroomInvitation | None: ...

    @abstractmethod
    async def get_by_token(self, token: str) -> ClassroomInvitation | None: ...

    @abstractmethod
    async def list_by_classroom(
        self, classroom_id: UUID, status: str | None = None
    ) -> list[ClassroomInvitation]: ...

    @abstractmethod
    async def list_pending_for_email(self, email: str) -> list[ClassroomInvitation]: ...

    @abstractmethod
    async def update(self, invitation: ClassroomInvitation) -> ClassroomInvitation: ...


class AbstractFolderRepository(ABC):
    @abstractmethod
    async def create(self, folder: Folder) -> Folder: ...

    @abstractmethod
    async def get_by_id(self, folder_id: UUID) -> Folder | None: ...

    @abstractmethod
    async def list_by_classroom(
        self, classroom_id: UUID, parent_id: UUID | None = None, include_deleted: bool = False
    ) -> list[Folder]: ...

    @abstractmethod
    async def update(self, folder: Folder) -> Folder: ...

    @abstractmethod
    async def delete(self, folder_id: UUID) -> None: ...


class AbstractMaterialRepository(ABC):
    @abstractmethod
    async def create(self, material: Material) -> Material: ...

    @abstractmethod
    async def get_by_id(self, material_id: UUID) -> Material | None: ...

    @abstractmethod
    async def list_by_classroom(
        self,
        classroom_id: UUID,
        folder_id: UUID | None = None,
        category: str | None = None,
        search: str | None = None,
        include_deleted: bool = False,
        only_deleted: bool = False,
        page: int = 1,
        limit: int = 50,
        sort: str = "created_at",
        descending: bool = True,
    ) -> tuple[list[Material], int]: ...

    @abstractmethod
    async def update(self, material: Material) -> Material: ...

    @abstractmethod
    async def delete(self, material_id: UUID) -> None: ...

    @abstractmethod
    async def add_version(self, version: MaterialVersion) -> MaterialVersion: ...

    @abstractmethod
    async def list_versions(self, material_id: UUID) -> list[MaterialVersion]: ...

    @abstractmethod
    async def increment_downloads(self, material_id: UUID) -> None: ...


class AbstractBookmarkRepository(ABC):
    @abstractmethod
    async def add(self, bookmark: Bookmark) -> Bookmark: ...

    @abstractmethod
    async def remove(self, user_id: UUID, material_id: UUID) -> None: ...

    @abstractmethod
    async def exists(self, user_id: UUID, material_id: UUID) -> bool: ...

    @abstractmethod
    async def list_material_ids(self, user_id: UUID) -> list[UUID]: ...


class AbstractMaterialViewRepository(ABC):
    @abstractmethod
    async def record_view(
        self, user_id: UUID, material_id: UUID, progress: float | None = None
    ) -> MaterialView: ...

    @abstractmethod
    async def list_recent(self, user_id: UUID, limit: int = 10) -> list[MaterialView]: ...

    @abstractmethod
    async def list_in_progress(self, user_id: UUID, limit: int = 10) -> list[MaterialView]: ...


class AbstractCourseworkRepository(ABC):
    @abstractmethod
    async def create(self, coursework: Coursework) -> Coursework: ...

    @abstractmethod
    async def get_by_id(self, coursework_id: UUID) -> Coursework | None: ...

    @abstractmethod
    async def list_by_classroom(
        self,
        classroom_id: UUID,
        type: str | None = None,
        status: str | None = None,
        search: str | None = None,
        include_deleted: bool = False,
        page: int = 1,
        limit: int = 50,
    ) -> tuple[list[Coursework], int]: ...

    @abstractmethod
    async def update(self, coursework: Coursework, expected_version: int | None = None) -> Coursework:
        """Persist; when expected_version is given, raise ConcurrencyConflict on mismatch."""
        ...

    @abstractmethod
    async def delete(self, coursework_id: UUID) -> None: ...

    @abstractmethod
    async def list_scheduled_due(self, now: datetime) -> list[Coursework]: ...

    @abstractmethod
    async def add_attachment(self, attachment: CourseworkAttachment) -> CourseworkAttachment: ...

    @abstractmethod
    async def list_attachments(self, coursework_id: UUID) -> list[CourseworkAttachment]: ...

    @abstractmethod
    async def delete_attachment(self, attachment_id: UUID) -> None: ...

    @abstractmethod
    async def upsert_poll_vote(self, vote: PollVote) -> PollVote: ...

    @abstractmethod
    async def poll_results(self, coursework_id: UUID) -> dict[int, int]: ...

    @abstractmethod
    async def get_poll_vote(self, coursework_id: UUID, user_id: UUID) -> PollVote | None: ...


class AbstractSubmissionRepository(ABC):
    @abstractmethod
    async def create(self, submission: Submission) -> Submission: ...

    @abstractmethod
    async def get_by_id(self, submission_id: UUID) -> Submission | None: ...

    @abstractmethod
    async def get_for_student(
        self, coursework_id: UUID, student_id: UUID
    ) -> Submission | None: ...

    @abstractmethod
    async def list_by_coursework(
        self, coursework_id: UUID, status: str | None = None, page: int = 1, limit: int = 50
    ) -> tuple[list[Submission], int]: ...

    @abstractmethod
    async def list_by_student(
        self, student_id: UUID, classroom_id: UUID | None = None, page: int = 1, limit: int = 50
    ) -> tuple[list[Submission], int]: ...

    @abstractmethod
    async def update(self, submission: Submission) -> Submission: ...

    @abstractmethod
    async def add_attachment(self, attachment: SubmissionAttachment) -> SubmissionAttachment: ...

    @abstractmethod
    async def list_attachments(self, submission_id: UUID) -> list[SubmissionAttachment]: ...

    @abstractmethod
    async def clear_attachments(self, submission_id: UUID) -> list[SubmissionAttachment]:
        """Delete all attachment rows; returns them so callers can remove stored files."""
        ...

    @abstractmethod
    async def add_grade(self, grade: Grade) -> Grade: ...

    @abstractmethod
    async def list_grades(self, submission_id: UUID) -> list[Grade]: ...

    @abstractmethod
    async def latest_grade(self, submission_id: UUID) -> Grade | None: ...

    @abstractmethod
    async def count_by_status(self, coursework_id: UUID) -> dict[str, int]: ...

    @abstractmethod
    async def average_score(self, coursework_id: UUID) -> float | None: ...


class AbstractCommentRepository(ABC):
    @abstractmethod
    async def create(self, comment: Comment) -> Comment: ...

    @abstractmethod
    async def get_by_id(self, comment_id: UUID) -> Comment | None: ...

    @abstractmethod
    async def list(
        self,
        classroom_id: UUID,
        coursework_id: UUID | None = None,
        parent_id: UUID | None = None,
        search: str | None = None,
        page: int = 1,
        limit: int = 50,
    ) -> tuple[list[Comment], int]: ...

    @abstractmethod
    async def update(self, comment: Comment) -> Comment: ...

    @abstractmethod
    async def add_reaction(self, reaction: CommentReaction) -> CommentReaction: ...

    @abstractmethod
    async def remove_reaction(self, comment_id: UUID, user_id: UUID, emoji: str) -> None: ...

    @abstractmethod
    async def reaction_summary(self, comment_id: UUID) -> dict[str, int]: ...


class AbstractNotificationRepository(ABC):
    @abstractmethod
    async def create(self, notification: Notification) -> Notification: ...

    @abstractmethod
    async def create_many(self, notifications: list[Notification]) -> None: ...

    @abstractmethod
    async def list_for_user(
        self, user_id: UUID, unread_only: bool = False, page: int = 1, limit: int = 20
    ) -> tuple[list[Notification], int]: ...

    @abstractmethod
    async def unread_count(self, user_id: UUID) -> int: ...

    @abstractmethod
    async def mark_read(self, notification_id: UUID, user_id: UUID) -> None: ...

    @abstractmethod
    async def mark_all_read(self, user_id: UUID) -> None: ...


class AbstractAuthTokenRepository(ABC):
    @abstractmethod
    async def create(self, token: AuthToken) -> AuthToken: ...

    @abstractmethod
    async def get_by_hash(self, token_hash: str) -> AuthToken | None: ...

    @abstractmethod
    async def mark_used(self, token_id: UUID) -> None: ...

    @abstractmethod
    async def invalidate_for_user(self, user_id: UUID, purpose: str) -> None: ...


class AbstractSessionRepository(ABC):
    """Refresh-token sessions (reuses the ``sessions`` table from migration 001)."""

    @abstractmethod
    async def create(
        self,
        user_id: UUID,
        token_hash: str,
        expires_at: datetime,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None: ...

    @abstractmethod
    async def get_user_id_by_hash(self, token_hash: str) -> UUID | None:
        """Return the owning user if the session exists and has not expired."""
        ...

    @abstractmethod
    async def delete_by_hash(self, token_hash: str) -> None: ...

    @abstractmethod
    async def delete_for_user(self, user_id: UUID) -> None: ...


class AbstractAuditLogRepository(ABC):
    @abstractmethod
    async def record(
        self,
        action: str,
        user_id: UUID | None = None,
        resource: str | None = None,
        ip_address: str | None = None,
        status_code: int | None = None,
        extra: dict | None = None,
    ) -> None: ...

    @abstractmethod
    async def list(
        self,
        user_id: UUID | None = None,
        action: str | None = None,
        page: int = 1,
        limit: int = 50,
    ) -> tuple[list[dict], int]: ...


class AbstractLmsAnalyticsRepository(ABC):
    """Read-only aggregate queries for dashboards. Derived, never stored."""

    @abstractmethod
    async def coursework_stats(self, classroom_id: UUID) -> list[dict]: ...

    @abstractmethod
    async def inactive_students(self, classroom_id: UUID, since: datetime) -> list[User]: ...

    @abstractmethod
    async def recently_active_students(self, classroom_id: UUID, limit: int = 10) -> list[User]: ...

    @abstractmethod
    async def material_usage(self, classroom_id: UUID) -> list[dict]: ...

    @abstractmethod
    async def storage_usage(self) -> dict: ...
