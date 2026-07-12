"""Concrete SQLAlchemy repositories for the LMS layer."""
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import Select, delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

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
from src.domain.exceptions import ConcurrencyConflict
from src.domain.repositories.lms_repository import (
    AbstractAuditLogRepository,
    AbstractAuthTokenRepository,
    AbstractBookmarkRepository,
    AbstractClassroomTeacherRepository,
    AbstractCommentRepository,
    AbstractCourseworkRepository,
    AbstractFolderRepository,
    AbstractInstitutionRepository,
    AbstractInvitationRepository,
    AbstractLmsAnalyticsRepository,
    AbstractMaterialRepository,
    AbstractMaterialViewRepository,
    AbstractNotificationRepository,
    AbstractSessionRepository,
    AbstractSubmissionRepository,
)
from src.infrastructure.database.models.classroom import EnrollmentModel
from src.infrastructure.database.models.knowledge import DocumentModel
from src.infrastructure.database.models.lms import (
    AuthTokenModel,
    BookmarkModel,
    ClassroomInvitationModel,
    ClassroomTeacherModel,
    CommentModel,
    CommentReactionModel,
    CourseworkAttachmentModel,
    CourseworkModel,
    FolderModel,
    GradeModel,
    InstitutionModel,
    MaterialModel,
    MaterialVersionModel,
    MaterialViewModel,
    NotificationModel,
    PollVoteModel,
    SubmissionAttachmentModel,
    SubmissionModel,
)
from src.infrastructure.database.models.system import AuditLogModel, SessionModel
from src.infrastructure.database.models.user import UserModel
from src.infrastructure.database.repositories.user_repository import _to_entity as _user_to_entity


def _uuid(value: str | None) -> UUID | None:
    return UUID(value) if value else None


def _s(value: UUID | None) -> str | None:
    return str(value) if value else None


async def _paginate(db: AsyncSession, stmt: Select, page: int, limit: int) -> tuple[list, int]:
    total = (
        await db.execute(select(func.count()).select_from(stmt.order_by(None).subquery()))
    ).scalar_one()
    rows = (await db.execute(stmt.offset((page - 1) * limit).limit(limit))).scalars().all()
    return list(rows), int(total)


# ── Entity mappers ────────────────────────────────────────────────────────────

def _institution(m: InstitutionModel) -> Institution:
    e = Institution.__new__(Institution)
    e.id, e.name, e.address = UUID(m.id), m.name, m.address
    e.contact_email, e.is_active = m.contact_email, m.is_active
    e.created_at, e.updated_at = m.created_at, m.updated_at
    return e


def _teacher(m: ClassroomTeacherModel) -> ClassroomTeacher:
    e = ClassroomTeacher.__new__(ClassroomTeacher)
    e.id, e.classroom_id, e.teacher_id = UUID(m.id), UUID(m.classroom_id), UUID(m.teacher_id)
    e.role, e.created_at, e.updated_at = m.role, m.created_at, m.updated_at
    return e


def _invitation(m: ClassroomInvitationModel) -> ClassroomInvitation:
    e = ClassroomInvitation.__new__(ClassroomInvitation)
    e.id, e.classroom_id, e.email = UUID(m.id), UUID(m.classroom_id), m.email
    e.invited_by, e.role, e.status, e.token = UUID(m.invited_by), m.role, m.status, m.token
    e.created_at, e.updated_at = m.created_at, m.updated_at
    return e


def _folder(m: FolderModel) -> Folder:
    e = Folder.__new__(Folder)
    e.id, e.classroom_id, e.parent_id = UUID(m.id), UUID(m.classroom_id), _uuid(m.parent_id)
    e.name, e.is_deleted, e.deleted_at = m.name, m.is_deleted, m.deleted_at
    e.created_at, e.updated_at = m.created_at, m.updated_at
    return e


def _material(m: MaterialModel) -> Material:
    e = Material.__new__(Material)
    e.id, e.classroom_id, e.folder_id = UUID(m.id), UUID(m.classroom_id), _uuid(m.folder_id)
    e.uploaded_by, e.title, e.description = UUID(m.uploaded_by), m.title, m.description
    e.category, e.filename, e.file_type = m.category, m.filename, m.file_type
    e.file_size, e.storage_path, e.link_url = m.file_size, m.storage_path, m.link_url
    e.document_id, e.version, e.download_count = _uuid(m.document_id), m.version, m.download_count
    e.is_deleted, e.deleted_at = m.is_deleted, m.deleted_at
    e.created_at, e.updated_at = m.created_at, m.updated_at
    return e


def _material_version(m: MaterialVersionModel) -> MaterialVersion:
    e = MaterialVersion.__new__(MaterialVersion)
    e.id, e.material_id, e.version = UUID(m.id), UUID(m.material_id), m.version
    e.filename, e.file_size, e.storage_path = m.filename, m.file_size, m.storage_path
    e.uploaded_by, e.created_at = _uuid(m.uploaded_by), m.created_at
    return e


def _coursework(m: CourseworkModel) -> Coursework:
    e = Coursework.__new__(Coursework)
    e.id, e.classroom_id, e.author_id = UUID(m.id), UUID(m.classroom_id), UUID(m.author_id)
    e.type, e.title, e.body, e.status = m.type, m.title, m.body, m.status
    e.scheduled_at, e.published_at, e.due_at = m.scheduled_at, m.published_at, m.due_at
    e.allow_late, e.max_marks, e.rubric = m.allow_late, m.max_marks, m.rubric
    e.questions, e.poll_options, e.settings = m.questions, m.poll_options, m.settings or {}
    e.version, e.is_deleted, e.deleted_at = m.version, m.is_deleted, m.deleted_at
    e.created_at, e.updated_at = m.created_at, m.updated_at
    return e


def _cw_attachment(m: CourseworkAttachmentModel) -> CourseworkAttachment:
    e = CourseworkAttachment.__new__(CourseworkAttachment)
    e.id, e.coursework_id = UUID(m.id), UUID(m.coursework_id)
    e.material_id, e.link_url, e.title = _uuid(m.material_id), m.link_url, m.title
    e.created_at = m.created_at
    return e


def _submission(m: SubmissionModel) -> Submission:
    e = Submission.__new__(Submission)
    e.id, e.coursework_id, e.student_id = UUID(m.id), UUID(m.coursework_id), UUID(m.student_id)
    e.status, e.text_answer, e.attempt = m.status, m.text_answer, m.attempt
    e.is_late, e.submitted_at = m.is_late, m.submitted_at
    e.created_at, e.updated_at = m.created_at, m.updated_at
    return e


def _sub_attachment(m: SubmissionAttachmentModel) -> SubmissionAttachment:
    e = SubmissionAttachment.__new__(SubmissionAttachment)
    e.id, e.submission_id, e.filename = UUID(m.id), UUID(m.submission_id), m.filename
    e.file_type, e.file_size, e.storage_path = m.file_type, m.file_size, m.storage_path
    e.created_at = m.created_at
    return e


def _grade(m: GradeModel) -> Grade:
    e = Grade.__new__(Grade)
    e.id, e.submission_id, e.grader_id = UUID(m.id), UUID(m.submission_id), _uuid(m.grader_id)
    e.score, e.max_marks, e.rubric_scores = m.score, m.max_marks, m.rubric_scores
    e.comment, e.private_feedback = m.comment, m.private_feedback
    e.is_returned, e.is_regrade, e.created_at = m.is_returned, m.is_regrade, m.created_at
    return e


def _comment(m: CommentModel) -> Comment:
    e = Comment.__new__(Comment)
    e.id, e.classroom_id = UUID(m.id), UUID(m.classroom_id)
    e.coursework_id, e.parent_id = _uuid(m.coursework_id), _uuid(m.parent_id)
    e.author_id, e.body, e.mentions = UUID(m.author_id), m.body, m.mentions or []
    e.is_deleted, e.deleted_at = m.is_deleted, m.deleted_at
    e.created_at, e.updated_at = m.created_at, m.updated_at
    return e


def _notification(m: NotificationModel) -> Notification:
    e = Notification.__new__(Notification)
    e.id, e.user_id, e.type, e.title = UUID(m.id), UUID(m.user_id), m.type, m.title
    e.body, e.data, e.is_read, e.created_at = m.body, m.data or {}, m.is_read, m.created_at
    return e


def _material_view(m: MaterialViewModel) -> MaterialView:
    e = MaterialView.__new__(MaterialView)
    e.id, e.user_id, e.material_id = UUID(m.id), UUID(m.user_id), UUID(m.material_id)
    e.view_count, e.progress, e.last_viewed_at = m.view_count, m.progress, m.last_viewed_at
    return e


def _auth_token(m: AuthTokenModel) -> AuthToken:
    e = AuthToken.__new__(AuthToken)
    e.id, e.user_id, e.token_hash = UUID(m.id), UUID(m.user_id), m.token_hash
    e.purpose, e.expires_at, e.used_at, e.created_at = (
        m.purpose, m.expires_at, m.used_at, m.created_at,
    )
    return e


# ── Repositories ──────────────────────────────────────────────────────────────

class InstitutionRepository(AbstractInstitutionRepository):
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(self, institution: Institution) -> Institution:
        model = InstitutionModel(
            id=str(institution.id),
            name=institution.name,
            address=institution.address,
            contact_email=institution.contact_email,
            is_active=institution.is_active,
        )
        self._db.add(model)
        await self._db.flush()
        await self._db.refresh(model)
        return _institution(model)

    async def get_by_id(self, institution_id: UUID) -> Institution | None:
        m = (
            await self._db.execute(
                select(InstitutionModel).where(InstitutionModel.id == str(institution_id))
            )
        ).scalar_one_or_none()
        return _institution(m) if m else None

    async def list(
        self, page: int = 1, limit: int = 20, search: str | None = None
    ) -> tuple[list[Institution], int]:
        stmt = select(InstitutionModel).order_by(InstitutionModel.name.asc())
        if search:
            stmt = stmt.where(InstitutionModel.name.ilike(f"%{search}%"))
        rows, total = await _paginate(self._db, stmt, page, limit)
        return [_institution(m) for m in rows], total

    async def update(self, institution: Institution) -> Institution:
        m = (
            await self._db.execute(
                select(InstitutionModel).where(InstitutionModel.id == str(institution.id))
            )
        ).scalar_one()
        m.name = institution.name
        m.address = institution.address
        m.contact_email = institution.contact_email
        m.is_active = institution.is_active
        await self._db.flush()
        await self._db.refresh(m)
        return _institution(m)

    async def delete(self, institution_id: UUID) -> None:
        await self._db.execute(
            delete(InstitutionModel).where(InstitutionModel.id == str(institution_id))
        )
        await self._db.flush()


class ClassroomTeacherRepository(AbstractClassroomTeacherRepository):
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def add(self, membership: ClassroomTeacher) -> ClassroomTeacher:
        model = ClassroomTeacherModel(
            id=str(membership.id),
            classroom_id=str(membership.classroom_id),
            teacher_id=str(membership.teacher_id),
            role=membership.role,
        )
        self._db.add(model)
        await self._db.flush()
        await self._db.refresh(model)
        return _teacher(model)

    async def get(self, classroom_id: UUID, teacher_id: UUID) -> ClassroomTeacher | None:
        m = (
            await self._db.execute(
                select(ClassroomTeacherModel).where(
                    ClassroomTeacherModel.classroom_id == str(classroom_id),
                    ClassroomTeacherModel.teacher_id == str(teacher_id),
                )
            )
        ).scalar_one_or_none()
        return _teacher(m) if m else None

    async def list_by_classroom(self, classroom_id: UUID) -> list[ClassroomTeacher]:
        rows = (
            await self._db.execute(
                select(ClassroomTeacherModel)
                .where(ClassroomTeacherModel.classroom_id == str(classroom_id))
                .order_by(ClassroomTeacherModel.created_at.asc())
            )
        ).scalars().all()
        return [_teacher(m) for m in rows]

    async def list_classroom_ids_for_teacher(self, teacher_id: UUID) -> list[UUID]:
        rows = (
            await self._db.execute(
                select(ClassroomTeacherModel.classroom_id).where(
                    ClassroomTeacherModel.teacher_id == str(teacher_id)
                )
            )
        ).scalars().all()
        return [UUID(r) for r in rows]

    async def remove(self, classroom_id: UUID, teacher_id: UUID) -> None:
        await self._db.execute(
            delete(ClassroomTeacherModel).where(
                ClassroomTeacherModel.classroom_id == str(classroom_id),
                ClassroomTeacherModel.teacher_id == str(teacher_id),
            )
        )
        await self._db.flush()


class InvitationRepository(AbstractInvitationRepository):
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(self, invitation: ClassroomInvitation) -> ClassroomInvitation:
        model = ClassroomInvitationModel(
            id=str(invitation.id),
            classroom_id=str(invitation.classroom_id),
            email=invitation.email.lower(),
            invited_by=str(invitation.invited_by),
            role=invitation.role,
            status=invitation.status,
            token=invitation.token,
        )
        self._db.add(model)
        await self._db.flush()
        await self._db.refresh(model)
        return _invitation(model)

    async def get_by_id(self, invitation_id: UUID) -> ClassroomInvitation | None:
        m = (
            await self._db.execute(
                select(ClassroomInvitationModel).where(
                    ClassroomInvitationModel.id == str(invitation_id)
                )
            )
        ).scalar_one_or_none()
        return _invitation(m) if m else None

    async def get_by_token(self, token: str) -> ClassroomInvitation | None:
        m = (
            await self._db.execute(
                select(ClassroomInvitationModel).where(ClassroomInvitationModel.token == token)
            )
        ).scalar_one_or_none()
        return _invitation(m) if m else None

    async def list_by_classroom(
        self, classroom_id: UUID, status: str | None = None
    ) -> list[ClassroomInvitation]:
        stmt = select(ClassroomInvitationModel).where(
            ClassroomInvitationModel.classroom_id == str(classroom_id)
        )
        if status:
            stmt = stmt.where(ClassroomInvitationModel.status == status)
        rows = (
            await self._db.execute(stmt.order_by(ClassroomInvitationModel.created_at.desc()))
        ).scalars().all()
        return [_invitation(m) for m in rows]

    async def list_pending_for_email(self, email: str) -> list[ClassroomInvitation]:
        rows = (
            await self._db.execute(
                select(ClassroomInvitationModel).where(
                    ClassroomInvitationModel.email == email.lower(),
                    ClassroomInvitationModel.status == "pending",
                )
            )
        ).scalars().all()
        return [_invitation(m) for m in rows]

    async def update(self, invitation: ClassroomInvitation) -> ClassroomInvitation:
        m = (
            await self._db.execute(
                select(ClassroomInvitationModel).where(
                    ClassroomInvitationModel.id == str(invitation.id)
                )
            )
        ).scalar_one()
        m.status = invitation.status
        m.role = invitation.role
        await self._db.flush()
        await self._db.refresh(m)
        return _invitation(m)


class FolderRepository(AbstractFolderRepository):
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(self, folder: Folder) -> Folder:
        model = FolderModel(
            id=str(folder.id),
            classroom_id=str(folder.classroom_id),
            parent_id=_s(folder.parent_id),
            name=folder.name,
        )
        self._db.add(model)
        await self._db.flush()
        await self._db.refresh(model)
        return _folder(model)

    async def get_by_id(self, folder_id: UUID) -> Folder | None:
        m = (
            await self._db.execute(select(FolderModel).where(FolderModel.id == str(folder_id)))
        ).scalar_one_or_none()
        return _folder(m) if m else None

    async def list_by_classroom(
        self, classroom_id: UUID, parent_id: UUID | None = None, include_deleted: bool = False
    ) -> list[Folder]:
        stmt = select(FolderModel).where(FolderModel.classroom_id == str(classroom_id))
        if parent_id is not None:
            stmt = stmt.where(FolderModel.parent_id == str(parent_id))
        if not include_deleted:
            stmt = stmt.where(FolderModel.is_deleted.is_(False))
        rows = (await self._db.execute(stmt.order_by(FolderModel.name.asc()))).scalars().all()
        return [_folder(m) for m in rows]

    async def update(self, folder: Folder) -> Folder:
        m = (
            await self._db.execute(select(FolderModel).where(FolderModel.id == str(folder.id)))
        ).scalar_one()
        m.name = folder.name
        m.parent_id = _s(folder.parent_id)
        m.is_deleted = folder.is_deleted
        m.deleted_at = folder.deleted_at
        await self._db.flush()
        await self._db.refresh(m)
        return _folder(m)

    async def delete(self, folder_id: UUID) -> None:
        await self._db.execute(delete(FolderModel).where(FolderModel.id == str(folder_id)))
        await self._db.flush()


_MATERIAL_SORTS = {
    "created_at": MaterialModel.created_at,
    "updated_at": MaterialModel.updated_at,
    "title": MaterialModel.title,
    "file_size": MaterialModel.file_size,
    "download_count": MaterialModel.download_count,
}


class MaterialRepository(AbstractMaterialRepository):
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(self, material: Material) -> Material:
        model = MaterialModel(
            id=str(material.id),
            classroom_id=str(material.classroom_id),
            folder_id=_s(material.folder_id),
            uploaded_by=str(material.uploaded_by),
            title=material.title,
            description=material.description,
            category=material.category,
            filename=material.filename,
            file_type=material.file_type,
            file_size=material.file_size,
            storage_path=material.storage_path,
            link_url=material.link_url,
            document_id=_s(material.document_id),
            version=material.version,
        )
        self._db.add(model)
        await self._db.flush()
        await self._db.refresh(model)
        return _material(model)

    async def get_by_id(self, material_id: UUID) -> Material | None:
        m = (
            await self._db.execute(
                select(MaterialModel).where(MaterialModel.id == str(material_id))
            )
        ).scalar_one_or_none()
        return _material(m) if m else None

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
    ) -> tuple[list[Material], int]:
        stmt = select(MaterialModel).where(MaterialModel.classroom_id == str(classroom_id))
        if folder_id is not None:
            stmt = stmt.where(MaterialModel.folder_id == str(folder_id))
        if category:
            stmt = stmt.where(MaterialModel.category == category)
        if search:
            pattern = f"%{search}%"
            stmt = stmt.where(
                or_(MaterialModel.title.ilike(pattern), MaterialModel.description.ilike(pattern))
            )
        if only_deleted:
            stmt = stmt.where(MaterialModel.is_deleted.is_(True))
        elif not include_deleted:
            stmt = stmt.where(MaterialModel.is_deleted.is_(False))
        col = _MATERIAL_SORTS.get(sort, MaterialModel.created_at)
        stmt = stmt.order_by(col.desc() if descending else col.asc())
        rows, total = await _paginate(self._db, stmt, page, limit)
        return [_material(m) for m in rows], total

    async def update(self, material: Material) -> Material:
        m = (
            await self._db.execute(
                select(MaterialModel).where(MaterialModel.id == str(material.id))
            )
        ).scalar_one()
        m.folder_id = _s(material.folder_id)
        m.title = material.title
        m.description = material.description
        m.category = material.category
        m.filename = material.filename
        m.file_type = material.file_type
        m.file_size = material.file_size
        m.storage_path = material.storage_path
        m.link_url = material.link_url
        m.version = material.version
        m.is_deleted = material.is_deleted
        m.deleted_at = material.deleted_at
        await self._db.flush()
        await self._db.refresh(m)
        return _material(m)

    async def delete(self, material_id: UUID) -> None:
        await self._db.execute(delete(MaterialModel).where(MaterialModel.id == str(material_id)))
        await self._db.flush()

    async def add_version(self, version: MaterialVersion) -> MaterialVersion:
        model = MaterialVersionModel(
            id=str(version.id),
            material_id=str(version.material_id),
            version=version.version,
            filename=version.filename,
            file_size=version.file_size,
            storage_path=version.storage_path,
            uploaded_by=_s(version.uploaded_by),
        )
        self._db.add(model)
        await self._db.flush()
        await self._db.refresh(model)
        return _material_version(model)

    async def list_versions(self, material_id: UUID) -> list[MaterialVersion]:
        rows = (
            await self._db.execute(
                select(MaterialVersionModel)
                .where(MaterialVersionModel.material_id == str(material_id))
                .order_by(MaterialVersionModel.version.desc())
            )
        ).scalars().all()
        return [_material_version(m) for m in rows]

    async def increment_downloads(self, material_id: UUID) -> None:
        await self._db.execute(
            update(MaterialModel)
            .where(MaterialModel.id == str(material_id))
            .values(download_count=MaterialModel.download_count + 1)
        )
        await self._db.flush()


class BookmarkRepository(AbstractBookmarkRepository):
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def add(self, bookmark: Bookmark) -> Bookmark:
        model = BookmarkModel(
            id=str(bookmark.id),
            user_id=str(bookmark.user_id),
            material_id=str(bookmark.material_id),
        )
        self._db.add(model)
        await self._db.flush()
        return bookmark

    async def remove(self, user_id: UUID, material_id: UUID) -> None:
        await self._db.execute(
            delete(BookmarkModel).where(
                BookmarkModel.user_id == str(user_id),
                BookmarkModel.material_id == str(material_id),
            )
        )
        await self._db.flush()

    async def exists(self, user_id: UUID, material_id: UUID) -> bool:
        count = (
            await self._db.execute(
                select(func.count())
                .select_from(BookmarkModel)
                .where(
                    BookmarkModel.user_id == str(user_id),
                    BookmarkModel.material_id == str(material_id),
                )
            )
        ).scalar_one()
        return int(count) > 0

    async def list_material_ids(self, user_id: UUID) -> list[UUID]:
        rows = (
            await self._db.execute(
                select(BookmarkModel.material_id)
                .where(BookmarkModel.user_id == str(user_id))
                .order_by(BookmarkModel.created_at.desc())
            )
        ).scalars().all()
        return [UUID(r) for r in rows]


class MaterialViewRepository(AbstractMaterialViewRepository):
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def record_view(
        self, user_id: UUID, material_id: UUID, progress: float | None = None
    ) -> MaterialView:
        m = (
            await self._db.execute(
                select(MaterialViewModel).where(
                    MaterialViewModel.user_id == str(user_id),
                    MaterialViewModel.material_id == str(material_id),
                )
            )
        ).scalar_one_or_none()
        if m:
            m.view_count += 1
            m.last_viewed_at = datetime.now(UTC)
            if progress is not None:
                m.progress = max(0.0, min(1.0, progress))
        else:
            m = MaterialViewModel(
                user_id=str(user_id),
                material_id=str(material_id),
                progress=max(0.0, min(1.0, progress or 0.0)),
            )
            self._db.add(m)
        await self._db.flush()
        await self._db.refresh(m)
        return _material_view(m)

    async def list_recent(self, user_id: UUID, limit: int = 10) -> list[MaterialView]:
        rows = (
            await self._db.execute(
                select(MaterialViewModel)
                .where(MaterialViewModel.user_id == str(user_id))
                .order_by(MaterialViewModel.last_viewed_at.desc())
                .limit(limit)
            )
        ).scalars().all()
        return [_material_view(m) for m in rows]

    async def list_in_progress(self, user_id: UUID, limit: int = 10) -> list[MaterialView]:
        rows = (
            await self._db.execute(
                select(MaterialViewModel)
                .where(
                    MaterialViewModel.user_id == str(user_id),
                    MaterialViewModel.progress > 0,
                    MaterialViewModel.progress < 1,
                )
                .order_by(MaterialViewModel.last_viewed_at.desc())
                .limit(limit)
            )
        ).scalars().all()
        return [_material_view(m) for m in rows]


class CourseworkRepository(AbstractCourseworkRepository):
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(self, coursework: Coursework) -> Coursework:
        model = CourseworkModel(
            id=str(coursework.id),
            classroom_id=str(coursework.classroom_id),
            author_id=str(coursework.author_id),
            type=coursework.type,
            title=coursework.title,
            body=coursework.body,
            status=coursework.status,
            scheduled_at=coursework.scheduled_at,
            published_at=coursework.published_at,
            due_at=coursework.due_at,
            allow_late=coursework.allow_late,
            max_marks=coursework.max_marks,
            rubric=coursework.rubric,
            questions=coursework.questions,
            poll_options=coursework.poll_options,
            settings=coursework.settings,
            version=coursework.version,
        )
        self._db.add(model)
        await self._db.flush()
        await self._db.refresh(model)
        return _coursework(model)

    async def get_by_id(self, coursework_id: UUID) -> Coursework | None:
        m = (
            await self._db.execute(
                select(CourseworkModel).where(CourseworkModel.id == str(coursework_id))
            )
        ).scalar_one_or_none()
        return _coursework(m) if m else None

    async def list_by_classroom(
        self,
        classroom_id: UUID,
        type: str | None = None,
        status: str | None = None,
        search: str | None = None,
        include_deleted: bool = False,
        page: int = 1,
        limit: int = 50,
    ) -> tuple[list[Coursework], int]:
        stmt = select(CourseworkModel).where(CourseworkModel.classroom_id == str(classroom_id))
        if type:
            stmt = stmt.where(CourseworkModel.type == type)
        if status:
            stmt = stmt.where(CourseworkModel.status == status)
        if search:
            pattern = f"%{search}%"
            stmt = stmt.where(
                or_(CourseworkModel.title.ilike(pattern), CourseworkModel.body.ilike(pattern))
            )
        if not include_deleted:
            stmt = stmt.where(CourseworkModel.is_deleted.is_(False))
        stmt = stmt.order_by(CourseworkModel.created_at.desc())
        rows, total = await _paginate(self._db, stmt, page, limit)
        return [_coursework(m) for m in rows], total

    async def update(
        self, coursework: Coursework, expected_version: int | None = None
    ) -> Coursework:
        m = (
            await self._db.execute(
                select(CourseworkModel).where(CourseworkModel.id == str(coursework.id))
            )
        ).scalar_one()
        if expected_version is not None and m.version != expected_version:
            raise ConcurrencyConflict(
                "Coursework was modified by someone else — reload and retry",
                details={"current_version": m.version, "expected_version": expected_version},
            )
        m.title = coursework.title
        m.body = coursework.body
        m.status = coursework.status
        m.scheduled_at = coursework.scheduled_at
        m.published_at = coursework.published_at
        m.due_at = coursework.due_at
        m.allow_late = coursework.allow_late
        m.max_marks = coursework.max_marks
        m.rubric = coursework.rubric
        m.questions = coursework.questions
        m.poll_options = coursework.poll_options
        m.settings = coursework.settings
        m.is_deleted = coursework.is_deleted
        m.deleted_at = coursework.deleted_at
        m.version = m.version + 1
        await self._db.flush()
        await self._db.refresh(m)
        return _coursework(m)

    async def delete(self, coursework_id: UUID) -> None:
        await self._db.execute(
            delete(CourseworkModel).where(CourseworkModel.id == str(coursework_id))
        )
        await self._db.flush()

    async def list_scheduled_due(self, now: datetime) -> list[Coursework]:
        rows = (
            await self._db.execute(
                select(CourseworkModel).where(
                    CourseworkModel.status == "scheduled",
                    CourseworkModel.scheduled_at <= now,
                    CourseworkModel.is_deleted.is_(False),
                )
            )
        ).scalars().all()
        return [_coursework(m) for m in rows]

    async def add_attachment(self, attachment: CourseworkAttachment) -> CourseworkAttachment:
        model = CourseworkAttachmentModel(
            id=str(attachment.id),
            coursework_id=str(attachment.coursework_id),
            material_id=_s(attachment.material_id),
            link_url=attachment.link_url,
            title=attachment.title,
        )
        self._db.add(model)
        await self._db.flush()
        await self._db.refresh(model)
        return _cw_attachment(model)

    async def list_attachments(self, coursework_id: UUID) -> list[CourseworkAttachment]:
        rows = (
            await self._db.execute(
                select(CourseworkAttachmentModel)
                .where(CourseworkAttachmentModel.coursework_id == str(coursework_id))
                .order_by(CourseworkAttachmentModel.created_at.asc())
            )
        ).scalars().all()
        return [_cw_attachment(m) for m in rows]

    async def delete_attachment(self, attachment_id: UUID) -> None:
        await self._db.execute(
            delete(CourseworkAttachmentModel).where(
                CourseworkAttachmentModel.id == str(attachment_id)
            )
        )
        await self._db.flush()

    async def upsert_poll_vote(self, vote: PollVote) -> PollVote:
        m = (
            await self._db.execute(
                select(PollVoteModel).where(
                    PollVoteModel.coursework_id == str(vote.coursework_id),
                    PollVoteModel.user_id == str(vote.user_id),
                )
            )
        ).scalar_one_or_none()
        if m:
            m.option_index = vote.option_index
        else:
            m = PollVoteModel(
                id=str(vote.id),
                coursework_id=str(vote.coursework_id),
                user_id=str(vote.user_id),
                option_index=vote.option_index,
            )
            self._db.add(m)
        await self._db.flush()
        return vote

    async def poll_results(self, coursework_id: UUID) -> dict[int, int]:
        rows = (
            await self._db.execute(
                select(PollVoteModel.option_index, func.count())
                .where(PollVoteModel.coursework_id == str(coursework_id))
                .group_by(PollVoteModel.option_index)
            )
        ).all()
        return {int(option): int(count) for option, count in rows}

    async def get_poll_vote(self, coursework_id: UUID, user_id: UUID) -> PollVote | None:
        m = (
            await self._db.execute(
                select(PollVoteModel).where(
                    PollVoteModel.coursework_id == str(coursework_id),
                    PollVoteModel.user_id == str(user_id),
                )
            )
        ).scalar_one_or_none()
        if not m:
            return None
        v = PollVote.__new__(PollVote)
        v.id, v.coursework_id, v.user_id = UUID(m.id), UUID(m.coursework_id), UUID(m.user_id)
        v.option_index, v.created_at = m.option_index, m.created_at
        return v


class SubmissionRepository(AbstractSubmissionRepository):
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(self, submission: Submission) -> Submission:
        model = SubmissionModel(
            id=str(submission.id),
            coursework_id=str(submission.coursework_id),
            student_id=str(submission.student_id),
            status=submission.status,
            text_answer=submission.text_answer,
            attempt=submission.attempt,
            is_late=submission.is_late,
            submitted_at=submission.submitted_at,
        )
        self._db.add(model)
        await self._db.flush()
        await self._db.refresh(model)
        return _submission(model)

    async def get_by_id(self, submission_id: UUID) -> Submission | None:
        m = (
            await self._db.execute(
                select(SubmissionModel).where(SubmissionModel.id == str(submission_id))
            )
        ).scalar_one_or_none()
        return _submission(m) if m else None

    async def get_for_student(
        self, coursework_id: UUID, student_id: UUID
    ) -> Submission | None:
        m = (
            await self._db.execute(
                select(SubmissionModel).where(
                    SubmissionModel.coursework_id == str(coursework_id),
                    SubmissionModel.student_id == str(student_id),
                )
            )
        ).scalar_one_or_none()
        return _submission(m) if m else None

    async def list_by_coursework(
        self, coursework_id: UUID, status: str | None = None, page: int = 1, limit: int = 50
    ) -> tuple[list[Submission], int]:
        stmt = select(SubmissionModel).where(
            SubmissionModel.coursework_id == str(coursework_id)
        )
        if status:
            stmt = stmt.where(SubmissionModel.status == status)
        stmt = stmt.order_by(SubmissionModel.submitted_at.desc().nulls_last())
        rows, total = await _paginate(self._db, stmt, page, limit)
        return [_submission(m) for m in rows], total

    async def list_by_student(
        self, student_id: UUID, classroom_id: UUID | None = None, page: int = 1, limit: int = 50
    ) -> tuple[list[Submission], int]:
        stmt = select(SubmissionModel).where(SubmissionModel.student_id == str(student_id))
        if classroom_id:
            stmt = stmt.join(
                CourseworkModel, CourseworkModel.id == SubmissionModel.coursework_id
            ).where(CourseworkModel.classroom_id == str(classroom_id))
        stmt = stmt.order_by(SubmissionModel.updated_at.desc())
        rows, total = await _paginate(self._db, stmt, page, limit)
        return [_submission(m) for m in rows], total

    async def update(self, submission: Submission) -> Submission:
        m = (
            await self._db.execute(
                select(SubmissionModel).where(SubmissionModel.id == str(submission.id))
            )
        ).scalar_one()
        m.status = submission.status
        m.text_answer = submission.text_answer
        m.attempt = submission.attempt
        m.is_late = submission.is_late
        m.submitted_at = submission.submitted_at
        await self._db.flush()
        await self._db.refresh(m)
        return _submission(m)

    async def add_attachment(self, attachment: SubmissionAttachment) -> SubmissionAttachment:
        model = SubmissionAttachmentModel(
            id=str(attachment.id),
            submission_id=str(attachment.submission_id),
            filename=attachment.filename,
            file_type=attachment.file_type,
            file_size=attachment.file_size,
            storage_path=attachment.storage_path,
        )
        self._db.add(model)
        await self._db.flush()
        await self._db.refresh(model)
        return _sub_attachment(model)

    async def list_attachments(self, submission_id: UUID) -> list[SubmissionAttachment]:
        rows = (
            await self._db.execute(
                select(SubmissionAttachmentModel)
                .where(SubmissionAttachmentModel.submission_id == str(submission_id))
                .order_by(SubmissionAttachmentModel.created_at.asc())
            )
        ).scalars().all()
        return [_sub_attachment(m) for m in rows]

    async def clear_attachments(self, submission_id: UUID) -> list[SubmissionAttachment]:
        existing = await self.list_attachments(submission_id)
        await self._db.execute(
            delete(SubmissionAttachmentModel).where(
                SubmissionAttachmentModel.submission_id == str(submission_id)
            )
        )
        await self._db.flush()
        return existing

    async def add_grade(self, grade: Grade) -> Grade:
        model = GradeModel(
            id=str(grade.id),
            submission_id=str(grade.submission_id),
            grader_id=_s(grade.grader_id),
            score=grade.score,
            max_marks=grade.max_marks,
            rubric_scores=grade.rubric_scores,
            comment=grade.comment,
            private_feedback=grade.private_feedback,
            is_returned=grade.is_returned,
            is_regrade=grade.is_regrade,
        )
        self._db.add(model)
        await self._db.flush()
        await self._db.refresh(model)
        return _grade(model)

    async def list_grades(self, submission_id: UUID) -> list[Grade]:
        rows = (
            await self._db.execute(
                select(GradeModel)
                .where(GradeModel.submission_id == str(submission_id))
                .order_by(GradeModel.created_at.desc())
            )
        ).scalars().all()
        return [_grade(m) for m in rows]

    async def latest_grade(self, submission_id: UUID) -> Grade | None:
        m = (
            await self._db.execute(
                select(GradeModel)
                .where(GradeModel.submission_id == str(submission_id))
                .order_by(GradeModel.created_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        return _grade(m) if m else None

    async def count_by_status(self, coursework_id: UUID) -> dict[str, int]:
        rows = (
            await self._db.execute(
                select(SubmissionModel.status, func.count())
                .where(SubmissionModel.coursework_id == str(coursework_id))
                .group_by(SubmissionModel.status)
            )
        ).all()
        return {status: int(count) for status, count in rows}

    async def average_score(self, coursework_id: UUID) -> float | None:
        # Latest grade per submission, averaged across the coursework.
        latest = (
            select(
                GradeModel.submission_id,
                func.max(GradeModel.created_at).label("latest_at"),
            )
            .join(SubmissionModel, SubmissionModel.id == GradeModel.submission_id)
            .where(SubmissionModel.coursework_id == str(coursework_id))
            .group_by(GradeModel.submission_id)
            .subquery()
        )
        result = (
            await self._db.execute(
                select(func.avg(GradeModel.score)).join(
                    latest,
                    (GradeModel.submission_id == latest.c.submission_id)
                    & (GradeModel.created_at == latest.c.latest_at),
                )
            )
        ).scalar_one_or_none()
        return float(result) if result is not None else None


class CommentRepository(AbstractCommentRepository):
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(self, comment: Comment) -> Comment:
        model = CommentModel(
            id=str(comment.id),
            classroom_id=str(comment.classroom_id),
            coursework_id=_s(comment.coursework_id),
            parent_id=_s(comment.parent_id),
            author_id=str(comment.author_id),
            body=comment.body,
            mentions=comment.mentions,
        )
        self._db.add(model)
        await self._db.flush()
        await self._db.refresh(model)
        return _comment(model)

    async def get_by_id(self, comment_id: UUID) -> Comment | None:
        m = (
            await self._db.execute(
                select(CommentModel).where(CommentModel.id == str(comment_id))
            )
        ).scalar_one_or_none()
        return _comment(m) if m else None

    async def list(
        self,
        classroom_id: UUID,
        coursework_id: UUID | None = None,
        parent_id: UUID | None = None,
        search: str | None = None,
        page: int = 1,
        limit: int = 50,
    ) -> tuple[list[Comment], int]:
        stmt = select(CommentModel).where(
            CommentModel.classroom_id == str(classroom_id),
            CommentModel.is_deleted.is_(False),
        )
        if coursework_id:
            stmt = stmt.where(CommentModel.coursework_id == str(coursework_id))
        if parent_id:
            stmt = stmt.where(CommentModel.parent_id == str(parent_id))
        elif not search:
            stmt = stmt.where(CommentModel.parent_id.is_(None))
        if search:
            stmt = stmt.where(CommentModel.body.ilike(f"%{search}%"))
        stmt = stmt.order_by(CommentModel.created_at.asc())
        rows, total = await _paginate(self._db, stmt, page, limit)
        return [_comment(m) for m in rows], total

    async def update(self, comment: Comment) -> Comment:
        m = (
            await self._db.execute(
                select(CommentModel).where(CommentModel.id == str(comment.id))
            )
        ).scalar_one()
        m.body = comment.body
        m.mentions = comment.mentions
        m.is_deleted = comment.is_deleted
        m.deleted_at = comment.deleted_at
        await self._db.flush()
        await self._db.refresh(m)
        return _comment(m)

    async def add_reaction(self, reaction: CommentReaction) -> CommentReaction:
        model = CommentReactionModel(
            id=str(reaction.id),
            comment_id=str(reaction.comment_id),
            user_id=str(reaction.user_id),
            emoji=reaction.emoji,
        )
        self._db.add(model)
        await self._db.flush()
        return reaction

    async def remove_reaction(self, comment_id: UUID, user_id: UUID, emoji: str) -> None:
        await self._db.execute(
            delete(CommentReactionModel).where(
                CommentReactionModel.comment_id == str(comment_id),
                CommentReactionModel.user_id == str(user_id),
                CommentReactionModel.emoji == emoji,
            )
        )
        await self._db.flush()

    async def reaction_summary(self, comment_id: UUID) -> dict[str, int]:
        rows = (
            await self._db.execute(
                select(CommentReactionModel.emoji, func.count())
                .where(CommentReactionModel.comment_id == str(comment_id))
                .group_by(CommentReactionModel.emoji)
            )
        ).all()
        return {emoji: int(count) for emoji, count in rows}


class NotificationRepository(AbstractNotificationRepository):
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    def _to_model(self, n: Notification) -> NotificationModel:
        return NotificationModel(
            id=str(n.id),
            user_id=str(n.user_id),
            type=n.type,
            title=n.title,
            body=n.body,
            data=n.data,
            is_read=n.is_read,
        )

    async def create(self, notification: Notification) -> Notification:
        self._db.add(self._to_model(notification))
        await self._db.flush()
        return notification

    async def create_many(self, notifications: list[Notification]) -> None:
        for n in notifications:
            self._db.add(self._to_model(n))
        await self._db.flush()

    async def list_for_user(
        self, user_id: UUID, unread_only: bool = False, page: int = 1, limit: int = 20
    ) -> tuple[list[Notification], int]:
        stmt = select(NotificationModel).where(NotificationModel.user_id == str(user_id))
        if unread_only:
            stmt = stmt.where(NotificationModel.is_read.is_(False))
        stmt = stmt.order_by(NotificationModel.created_at.desc())
        rows, total = await _paginate(self._db, stmt, page, limit)
        return [_notification(m) for m in rows], total

    async def unread_count(self, user_id: UUID) -> int:
        count = (
            await self._db.execute(
                select(func.count())
                .select_from(NotificationModel)
                .where(
                    NotificationModel.user_id == str(user_id),
                    NotificationModel.is_read.is_(False),
                )
            )
        ).scalar_one()
        return int(count)

    async def mark_read(self, notification_id: UUID, user_id: UUID) -> None:
        await self._db.execute(
            update(NotificationModel)
            .where(
                NotificationModel.id == str(notification_id),
                NotificationModel.user_id == str(user_id),
            )
            .values(is_read=True)
        )
        await self._db.flush()

    async def mark_all_read(self, user_id: UUID) -> None:
        await self._db.execute(
            update(NotificationModel)
            .where(NotificationModel.user_id == str(user_id))
            .values(is_read=True)
        )
        await self._db.flush()


class AuthTokenRepository(AbstractAuthTokenRepository):
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(self, token: AuthToken) -> AuthToken:
        model = AuthTokenModel(
            id=str(token.id),
            user_id=str(token.user_id),
            token_hash=token.token_hash,
            purpose=token.purpose,
            expires_at=token.expires_at,
        )
        self._db.add(model)
        await self._db.flush()
        return token

    async def get_by_hash(self, token_hash: str) -> AuthToken | None:
        m = (
            await self._db.execute(
                select(AuthTokenModel).where(AuthTokenModel.token_hash == token_hash)
            )
        ).scalar_one_or_none()
        return _auth_token(m) if m else None

    async def mark_used(self, token_id: UUID) -> None:
        await self._db.execute(
            update(AuthTokenModel)
            .where(AuthTokenModel.id == str(token_id))
            .values(used_at=datetime.now(UTC))
        )
        await self._db.flush()

    async def invalidate_for_user(self, user_id: UUID, purpose: str) -> None:
        await self._db.execute(
            update(AuthTokenModel)
            .where(
                AuthTokenModel.user_id == str(user_id),
                AuthTokenModel.purpose == purpose,
                AuthTokenModel.used_at.is_(None),
            )
            .values(used_at=datetime.now(UTC))
        )
        await self._db.flush()


class SessionRepository(AbstractSessionRepository):
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(
        self,
        user_id: UUID,
        token_hash: str,
        expires_at: datetime,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        self._db.add(
            SessionModel(
                user_id=str(user_id),
                token_hash=token_hash,
                expires_at=expires_at,
                ip_address=ip_address,
                user_agent=user_agent,
            )
        )
        await self._db.flush()

    async def get_user_id_by_hash(self, token_hash: str) -> UUID | None:
        m = (
            await self._db.execute(
                select(SessionModel).where(
                    SessionModel.token_hash == token_hash,
                    SessionModel.expires_at > datetime.now(UTC),
                )
            )
        ).scalar_one_or_none()
        return UUID(m.user_id) if m else None

    async def delete_by_hash(self, token_hash: str) -> None:
        await self._db.execute(
            delete(SessionModel).where(SessionModel.token_hash == token_hash)
        )
        await self._db.flush()

    async def delete_for_user(self, user_id: UUID) -> None:
        await self._db.execute(delete(SessionModel).where(SessionModel.user_id == str(user_id)))
        await self._db.flush()


class AuditLogRepository(AbstractAuditLogRepository):
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def record(
        self,
        action: str,
        user_id: UUID | None = None,
        resource: str | None = None,
        ip_address: str | None = None,
        status_code: int | None = None,
        extra: dict | None = None,
    ) -> None:
        self._db.add(
            AuditLogModel(
                user_id=_s(user_id),
                action=action,
                resource=resource,
                ip_address=ip_address,
                status_code=status_code,
                extra_data=extra,
            )
        )
        await self._db.flush()

    async def list(
        self,
        user_id: UUID | None = None,
        action: str | None = None,
        page: int = 1,
        limit: int = 50,
    ) -> tuple[list[dict], int]:
        stmt = select(AuditLogModel)
        if user_id:
            stmt = stmt.where(AuditLogModel.user_id == str(user_id))
        if action:
            stmt = stmt.where(AuditLogModel.action.ilike(f"%{action}%"))
        stmt = stmt.order_by(AuditLogModel.created_at.desc())
        rows, total = await _paginate(self._db, stmt, page, limit)
        return [
            {
                "id": m.id,
                "user_id": m.user_id,
                "action": m.action,
                "resource": m.resource,
                "ip_address": m.ip_address,
                "status_code": m.status_code,
                "extra": m.extra_data,
                "created_at": m.created_at.isoformat(),
            }
            for m in rows
        ], total


class LmsAnalyticsRepository(AbstractLmsAnalyticsRepository):
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def coursework_stats(self, classroom_id: UUID) -> list[dict]:
        gradeable = (
            await self._db.execute(
                select(CourseworkModel)
                .where(
                    CourseworkModel.classroom_id == str(classroom_id),
                    CourseworkModel.is_deleted.is_(False),
                    CourseworkModel.status == "published",
                    CourseworkModel.type.in_(
                        ["assignment", "homework", "quiz", "exam", "practice_set"]
                    ),
                )
                .order_by(CourseworkModel.created_at.desc())
            )
        ).scalars().all()

        out: list[dict] = []
        for cw in gradeable:
            counts = dict(
                (
                    await self._db.execute(
                        select(SubmissionModel.status, func.count())
                        .where(SubmissionModel.coursework_id == cw.id)
                        .group_by(SubmissionModel.status)
                    )
                ).all()
            )
            avg = (
                await self._db.execute(
                    select(func.avg(GradeModel.score))
                    .join(SubmissionModel, SubmissionModel.id == GradeModel.submission_id)
                    .where(SubmissionModel.coursework_id == cw.id)
                )
            ).scalar_one_or_none()
            out.append(
                {
                    "coursework_id": cw.id,
                    "title": cw.title,
                    "type": cw.type,
                    "due_at": cw.due_at.isoformat() if cw.due_at else None,
                    "max_marks": cw.max_marks,
                    "submitted": int(counts.get("submitted", 0)) + int(counts.get("returned", 0)),
                    "returned": int(counts.get("returned", 0)),
                    "average_score": float(avg) if avg is not None else None,
                }
            )
        return out

    async def inactive_students(self, classroom_id: UUID, since: datetime) -> list[User]:
        active_sub = (
            select(SubmissionModel.student_id)
            .join(CourseworkModel, CourseworkModel.id == SubmissionModel.coursework_id)
            .where(
                CourseworkModel.classroom_id == str(classroom_id),
                SubmissionModel.updated_at >= since,
            )
        )
        active_view = (
            select(MaterialViewModel.user_id)
            .join(MaterialModel, MaterialModel.id == MaterialViewModel.material_id)
            .where(
                MaterialModel.classroom_id == str(classroom_id),
                MaterialViewModel.last_viewed_at >= since,
            )
        )
        rows = (
            await self._db.execute(
                select(UserModel)
                .join(EnrollmentModel, EnrollmentModel.student_id == UserModel.id)
                .where(
                    EnrollmentModel.classroom_id == str(classroom_id),
                    EnrollmentModel.status == "active",
                    UserModel.id.notin_(active_sub),
                    UserModel.id.notin_(active_view),
                )
                .order_by(UserModel.username.asc())
            )
        ).scalars().all()
        return [_user_to_entity(m) for m in rows]

    async def recently_active_students(self, classroom_id: UUID, limit: int = 10) -> list[User]:
        latest = (
            select(
                MaterialViewModel.user_id.label("uid"),
                func.max(MaterialViewModel.last_viewed_at).label("at"),
            )
            .join(MaterialModel, MaterialModel.id == MaterialViewModel.material_id)
            .where(MaterialModel.classroom_id == str(classroom_id))
            .group_by(MaterialViewModel.user_id)
            .subquery()
        )
        rows = (
            await self._db.execute(
                select(UserModel)
                .join(latest, latest.c.uid == UserModel.id)
                .join(
                    EnrollmentModel,
                    (EnrollmentModel.student_id == UserModel.id)
                    & (EnrollmentModel.classroom_id == str(classroom_id)),
                )
                .order_by(latest.c.at.desc())
                .limit(limit)
            )
        ).scalars().all()
        return [_user_to_entity(m) for m in rows]

    async def material_usage(self, classroom_id: UUID) -> list[dict]:
        views = (
            select(
                MaterialViewModel.material_id.label("mid"),
                func.count().label("viewers"),
                func.sum(MaterialViewModel.view_count).label("views"),
            )
            .group_by(MaterialViewModel.material_id)
            .subquery()
        )
        bms = (
            select(BookmarkModel.material_id.label("mid"), func.count().label("bookmarks"))
            .group_by(BookmarkModel.material_id)
            .subquery()
        )
        rows = (
            await self._db.execute(
                select(
                    MaterialModel,
                    func.coalesce(views.c.views, 0),
                    func.coalesce(views.c.viewers, 0),
                    func.coalesce(bms.c.bookmarks, 0),
                )
                .outerjoin(views, views.c.mid == MaterialModel.id)
                .outerjoin(bms, bms.c.mid == MaterialModel.id)
                .where(
                    MaterialModel.classroom_id == str(classroom_id),
                    MaterialModel.is_deleted.is_(False),
                )
                .order_by(MaterialModel.download_count.desc())
            )
        ).all()
        return [
            {
                "material_id": m.id,
                "title": m.title,
                "category": m.category,
                "downloads": m.download_count,
                "views": int(views_count),
                "unique_viewers": int(viewers),
                "bookmarks": int(bookmarks),
            }
            for m, views_count, viewers, bookmarks in rows
        ]

    async def storage_usage(self) -> dict:
        docs = (
            await self._db.execute(
                select(func.coalesce(func.sum(DocumentModel.file_size), 0), func.count())
            )
        ).one()
        materials = (
            await self._db.execute(
                select(func.coalesce(func.sum(MaterialModel.file_size), 0), func.count())
            )
        ).one()
        subs = (
            await self._db.execute(
                select(
                    func.coalesce(func.sum(SubmissionAttachmentModel.file_size), 0),
                    func.count(),
                )
            )
        ).one()
        return {
            "documents": {"bytes": int(docs[0]), "count": int(docs[1])},
            "materials": {"bytes": int(materials[0]), "count": int(materials[1])},
            "submission_attachments": {"bytes": int(subs[0]), "count": int(subs[1])},
            "total_bytes": int(docs[0]) + int(materials[0]) + int(subs[0]),
        }
