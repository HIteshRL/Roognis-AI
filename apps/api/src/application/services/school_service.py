import re
import secrets
from uuid import UUID

import structlog

from src.domain.entities.school import Role, School, SchoolMember
from src.domain.exceptions import (
    AuthorizationError,
    DuplicateEntity,
    EntityNotFound,
)
from src.domain.repositories.school_repository import (
    AbstractSchoolMemberRepository,
    AbstractSchoolRepository,
)
from src.domain.repositories.user_repository import AbstractUserRepository

logger = structlog.get_logger(__name__)


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "school"


class SchoolService:
    def __init__(
        self,
        school_repo: AbstractSchoolRepository,
        member_repo: AbstractSchoolMemberRepository,
        user_repo: AbstractUserRepository,
    ) -> None:
        self._schools = school_repo
        self._members = member_repo
        self._users = user_repo

    async def create_school(
        self, owner_id: UUID, name: str, address: str | None
    ) -> tuple[School, str]:
        slug = _slugify(name)
        if await self._schools.get_by_slug(slug):
            slug = f"{slug}-{secrets.token_hex(3)}"

        school = await self._schools.create(
            School(name=name, slug=slug, address=address, created_by=owner_id)
        )
        await self._members.create(
            SchoolMember(school_id=school.id, user_id=owner_id, role=Role.SCHOOL_ADMIN)
        )
        await self._promote(owner_id, Role.SCHOOL_ADMIN)
        logger.info("school_created", school_id=str(school.id), owner_id=str(owner_id))
        return school, Role.SCHOOL_ADMIN

    async def list_my_schools(self, user_id: UUID) -> list[tuple[School, str]]:
        schools = await self._schools.list_for_member(user_id)
        out: list[tuple[School, str]] = []
        for s in schools:
            member = await self._members.get(s.id, user_id)
            out.append((s, member.role if member else Role.TEACHER))
        return out

    async def get_role(self, school_id: UUID, user_id: UUID) -> str | None:
        member = await self._members.get(school_id, user_id)
        return member.role if member else None

    async def require_admin(self, school_id: UUID, user_id: UUID) -> None:
        role = await self.get_role(school_id, user_id)
        if role != Role.SCHOOL_ADMIN:
            raise AuthorizationError("School admin access required")

    async def add_teacher(
        self, school_id: UUID, actor_id: UUID, email: str, role: str
    ) -> tuple[SchoolMember, str, str]:
        await self.require_admin(school_id, actor_id)
        if not await self._schools.get_by_id(school_id):
            raise EntityNotFound("School not found")

        user = await self._users.get_by_email(email)
        if not user:
            raise EntityNotFound("No user found with that email")
        if await self._members.get(school_id, user.id):
            raise DuplicateEntity("User is already a member of this school")

        target_role = role if role in Role.STAFF else Role.TEACHER
        member = await self._members.create(
            SchoolMember(school_id=school_id, user_id=user.id, role=target_role)
        )
        await self._promote(user.id, target_role)
        return member, user.email, user.username

    async def list_members(
        self, school_id: UUID, actor_id: UUID
    ) -> list[tuple[SchoolMember, str, str]]:
        if not await self._members.get(school_id, actor_id):
            raise AuthorizationError("Not a member of this school")
        members = await self._members.list_by_school(school_id)
        out: list[tuple[SchoolMember, str, str]] = []
        for m in members:
            user = await self._users.get_by_id(m.user_id)
            if user:
                out.append((m, user.email, user.username))
        return out

    async def _promote(self, user_id: UUID, role: str) -> None:
        """Raise the user's platform role, never demote a stronger one."""
        user = await self._users.get_by_id(user_id)
        if not user or user.is_admin:
            return
        rank = {Role.STUDENT: 0, Role.TEACHER: 1, Role.SCHOOL_ADMIN: 2}
        if rank.get(role, 0) > rank.get(user.role, 0):
            user.role = role
            await self._users.update(user)
