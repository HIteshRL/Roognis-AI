from uuid import UUID

import structlog

from src.domain.entities.school import Role, SyllabusItem
from src.domain.exceptions import AuthorizationError, EntityNotFound
from src.domain.repositories.school_repository import (
    AbstractClassroomRepository,
    AbstractEnrollmentRepository,
    AbstractSchoolMemberRepository,
    AbstractSyllabusRepository,
)

logger = structlog.get_logger(__name__)


class SyllabusService:
    def __init__(
        self,
        syllabus_repo: AbstractSyllabusRepository,
        classroom_repo: AbstractClassroomRepository,
        member_repo: AbstractSchoolMemberRepository,
        enrollment_repo: AbstractEnrollmentRepository,
    ) -> None:
        self._syllabus = syllabus_repo
        self._classrooms = classroom_repo
        self._members = member_repo
        self._enrollments = enrollment_repo

    async def add_item(
        self,
        classroom_id: UUID,
        user_id: UUID,
        subject: str,
        chapter: str,
        topic: str | None,
        description: str | None,
        order_index: int,
        knowledge_base_id: UUID | None,
        is_published: bool,
    ) -> SyllabusItem:
        await self._assert_manage(classroom_id, user_id)
        return await self._syllabus.create(
            SyllabusItem(
                classroom_id=classroom_id,
                subject=subject,
                chapter=chapter,
                topic=topic,
                description=description,
                order_index=order_index,
                knowledge_base_id=knowledge_base_id,
                is_published=is_published,
            )
        )

    async def list_items(
        self, classroom_id: UUID, user_id: UUID
    ) -> list[SyllabusItem]:
        """Staff see all items; enrolled students see only published ones."""
        if await self._can_manage(classroom_id, user_id):
            return await self._syllabus.list_by_classroom(classroom_id)
        await self._assert_enrolled(classroom_id, user_id)
        return await self._syllabus.list_by_classroom(classroom_id, published_only=True)

    async def update_item(
        self,
        item_id: UUID,
        user_id: UUID,
        **fields: object,
    ) -> SyllabusItem:
        item = await self._syllabus.get_by_id(item_id)
        if not item:
            raise EntityNotFound("Syllabus item not found")
        await self._assert_manage(item.classroom_id, user_id)

        if fields.get("subject") is not None:
            item.subject = fields["subject"]  # type: ignore[assignment]
        if fields.get("chapter") is not None:
            item.chapter = fields["chapter"]  # type: ignore[assignment]
        if "topic" in fields and fields["topic"] is not None:
            item.topic = fields["topic"]  # type: ignore[assignment]
        if "description" in fields and fields["description"] is not None:
            item.description = fields["description"]  # type: ignore[assignment]
        if fields.get("order_index") is not None:
            item.order_index = fields["order_index"]  # type: ignore[assignment]
        if "knowledge_base_id" in fields and fields["knowledge_base_id"] is not None:
            item.knowledge_base_id = fields["knowledge_base_id"]  # type: ignore[assignment]
        if fields.get("is_published") is not None:
            item.is_published = fields["is_published"]  # type: ignore[assignment]
        return await self._syllabus.update(item)

    async def delete_item(self, item_id: UUID, user_id: UUID) -> None:
        item = await self._syllabus.get_by_id(item_id)
        if not item:
            raise EntityNotFound("Syllabus item not found")
        await self._assert_manage(item.classroom_id, user_id)
        await self._syllabus.delete(item_id)

    # ── Authorization ────────────────────────────────────────────────────────

    async def _can_manage(self, classroom_id: UUID, user_id: UUID) -> bool:
        classroom = await self._classrooms.get_by_id(classroom_id)
        if not classroom:
            raise EntityNotFound("Classroom not found")
        if classroom.teacher_id == user_id:
            return True
        member = await self._members.get(classroom.school_id, user_id)
        return bool(member and member.role == Role.SCHOOL_ADMIN)

    async def _assert_manage(self, classroom_id: UUID, user_id: UUID) -> None:
        if not await self._can_manage(classroom_id, user_id):
            raise AuthorizationError("You do not manage this classroom")

    async def _assert_enrolled(self, classroom_id: UUID, user_id: UUID) -> None:
        enrollment = await self._enrollments.get(classroom_id, user_id)
        if not enrollment or enrollment.status != "active":
            raise AuthorizationError("You are not enrolled in this classroom")
