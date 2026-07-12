"""
System administration — institutions, user management (suspend/delete),
classroom oversight, audit-log access, and storage usage.

Every mutating action writes an audit-log row (fail-open: an audit failure
never blocks the admin action itself).
"""
from uuid import UUID

import structlog

from src.application.dtos.admin import (
    AdminUserListResponse,
    AdminUserResponse,
    CreateInstitutionRequest,
    InstitutionResponse,
    UpdateInstitutionRequest,
)
from src.domain.entities.lms import Institution
from src.domain.entities.user import User
from src.domain.exceptions import EntityNotFound, ValidationError
from src.domain.repositories.classroom_repository import AbstractClassroomRepository
from src.domain.repositories.lms_repository import (
    AbstractAuditLogRepository,
    AbstractInstitutionRepository,
    AbstractLmsAnalyticsRepository,
)
from src.domain.repositories.user_repository import AbstractUserRepository

logger = structlog.get_logger(__name__)


class AdminService:
    def __init__(
        self,
        institution_repo: AbstractInstitutionRepository,
        user_repo: AbstractUserRepository,
        classroom_repo: AbstractClassroomRepository,
        audit_repo: AbstractAuditLogRepository,
        analytics_repo: AbstractLmsAnalyticsRepository,
    ) -> None:
        self._institutions = institution_repo
        self._users = user_repo
        self._classrooms = classroom_repo
        self._audit = audit_repo
        self._analytics = analytics_repo

    # ── Institutions ─────────────────────────────────────────────────────────

    async def create_institution(
        self, admin_id: UUID, dto: CreateInstitutionRequest
    ) -> InstitutionResponse:
        institution = await self._institutions.create(
            Institution(name=dto.name, address=dto.address, contact_email=dto.contact_email)
        )
        await self._record(admin_id, "institution.create", str(institution.id))
        return self._institution_to_response(institution)

    async def list_institutions(
        self, page: int = 1, limit: int = 20, search: str | None = None
    ) -> tuple[list[InstitutionResponse], int]:
        items, total = await self._institutions.list(page=page, limit=limit, search=search)
        return [self._institution_to_response(i) for i in items], total

    async def update_institution(
        self, admin_id: UUID, institution_id: UUID, dto: UpdateInstitutionRequest
    ) -> InstitutionResponse:
        institution = await self._institutions.get_by_id(institution_id)
        if not institution:
            raise EntityNotFound("Institution not found")
        if dto.name is not None:
            institution.name = dto.name
        if dto.address is not None:
            institution.address = dto.address
        if dto.contact_email is not None:
            institution.contact_email = dto.contact_email
        if dto.is_active is not None:
            institution.is_active = dto.is_active
        institution = await self._institutions.update(institution)
        await self._record(admin_id, "institution.update", str(institution_id))
        return self._institution_to_response(institution)

    async def delete_institution(self, admin_id: UUID, institution_id: UUID) -> None:
        await self._institutions.delete(institution_id)
        await self._record(admin_id, "institution.delete", str(institution_id))

    # ── Users ────────────────────────────────────────────────────────────────

    async def list_users(
        self,
        page: int = 1,
        limit: int = 50,
        role: str | None = None,
        search: str | None = None,
    ) -> AdminUserListResponse:
        users, total = await self._users.list(page=page, limit=limit, role=role, search=search)
        return AdminUserListResponse(
            items=[self._user_to_response(u) for u in users],
            total=total,
            page=page,
            limit=limit,
        )

    async def suspend_user(self, admin_id: UUID, user_id: UUID) -> AdminUserResponse:
        user = await self._get_user(user_id)
        if user.is_admin:
            raise ValidationError("Admins cannot be suspended")
        user.is_active = False
        user = await self._users.update(user)
        await self._record(admin_id, "user.suspend", str(user_id))
        logger.info("user_suspended", user_id=str(user_id), by=str(admin_id))
        return self._user_to_response(user)

    async def reactivate_user(self, admin_id: UUID, user_id: UUID) -> AdminUserResponse:
        user = await self._get_user(user_id)
        user.is_active = True
        user = await self._users.update(user)
        await self._record(admin_id, "user.reactivate", str(user_id))
        return self._user_to_response(user)

    async def delete_user(self, admin_id: UUID, user_id: UUID) -> None:
        user = await self._get_user(user_id)
        if user.is_admin:
            raise ValidationError("Admins cannot be deleted")
        await self._users.delete(user_id)
        await self._record(admin_id, "user.delete", str(user_id))
        logger.info("user_deleted", user_id=str(user_id), by=str(admin_id))

    # ── Classrooms ───────────────────────────────────────────────────────────

    async def list_classrooms(
        self,
        page: int = 1,
        limit: int = 50,
        search: str | None = None,
        include_deleted: bool = False,
    ) -> tuple[list[dict], int]:
        classrooms, total = await self._classrooms.list_all(
            page=page, limit=limit, search=search, include_deleted=include_deleted
        )
        out = []
        for c in classrooms:
            out.append(
                {
                    "id": str(c.id),
                    "name": c.name,
                    "teacher_id": str(c.teacher_id),
                    "subject": c.subject,
                    "grade": c.grade,
                    "is_archived": c.is_archived,
                    "is_deleted": c.is_deleted,
                    "student_count": await self._classrooms.count_students(c.id),
                    "created_at": c.created_at.isoformat(),
                }
            )
        return out, total

    async def restore_classroom(self, admin_id: UUID, classroom_id: UUID) -> None:
        classroom = await self._classrooms.get_by_id(classroom_id)
        if not classroom:
            raise EntityNotFound("Classroom not found")
        classroom.is_deleted = False
        classroom.deleted_at = None
        await self._classrooms.update(classroom)
        await self._record(admin_id, "classroom.restore", str(classroom_id))

    # ── Audit & storage ──────────────────────────────────────────────────────

    async def list_audit_logs(
        self,
        user_id: UUID | None = None,
        action: str | None = None,
        page: int = 1,
        limit: int = 50,
    ) -> tuple[list[dict], int]:
        return await self._audit.list(user_id=user_id, action=action, page=page, limit=limit)

    async def storage_usage(self) -> dict:
        return await self._analytics.storage_usage()

    # ── Helpers ──────────────────────────────────────────────────────────────

    async def _get_user(self, user_id: UUID) -> User:
        user = await self._users.get_by_id(user_id)
        if not user:
            raise EntityNotFound("User not found")
        return user

    async def _record(self, admin_id: UUID, action: str, resource: str) -> None:
        try:
            await self._audit.record(action=action, user_id=admin_id, resource=resource)
        except Exception as exc:
            logger.warning("audit_record_failed", action=action, error=str(exc))

    @staticmethod
    def _institution_to_response(i: Institution) -> InstitutionResponse:
        return InstitutionResponse(
            id=str(i.id),
            name=i.name,
            address=i.address,
            contact_email=i.contact_email,
            is_active=i.is_active,
            created_at=i.created_at.isoformat(),
        )

    @staticmethod
    def _user_to_response(u: User) -> AdminUserResponse:
        return AdminUserResponse(
            id=str(u.id),
            email=u.email,
            username=u.username,
            role=u.role,
            is_active=u.is_active,
            is_verified=u.is_verified,
            is_admin=u.is_admin,
            created_at=u.created_at.isoformat(),
        )
