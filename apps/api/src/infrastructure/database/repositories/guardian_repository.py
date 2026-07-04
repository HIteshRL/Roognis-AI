from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.guardian import GuardianLink
from src.domain.repositories.guardian_repository import AbstractGuardianRepository
from src.infrastructure.database.models.guardian import GuardianLinkModel


def _to_link(m: GuardianLinkModel) -> GuardianLink:
    link = GuardianLink.__new__(GuardianLink)
    link.id = UUID(m.id)
    link.parent_id = UUID(m.parent_id)
    link.student_id = UUID(m.student_id)
    link.status = m.status
    link.created_at = m.created_at
    link.updated_at = m.updated_at
    return link


class GuardianRepository(AbstractGuardianRepository):
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(self, link: GuardianLink) -> GuardianLink:
        m = GuardianLinkModel(
            id=str(link.id),
            parent_id=str(link.parent_id),
            student_id=str(link.student_id),
            status=link.status,
        )
        self._db.add(m)
        await self._db.flush()
        await self._db.refresh(m)
        return _to_link(m)

    async def get(self, parent_id: UUID, student_id: UUID) -> GuardianLink | None:
        result = await self._db.execute(
            select(GuardianLinkModel).where(
                GuardianLinkModel.parent_id == str(parent_id),
                GuardianLinkModel.student_id == str(student_id),
            )
        )
        m = result.scalar_one_or_none()
        return _to_link(m) if m else None

    async def list_by_parent(self, parent_id: UUID) -> list[GuardianLink]:
        result = await self._db.execute(
            select(GuardianLinkModel)
            .where(
                GuardianLinkModel.parent_id == str(parent_id),
                GuardianLinkModel.status == "active",
            )
            .order_by(GuardianLinkModel.created_at.desc())
        )
        return [_to_link(m) for m in result.scalars().all()]

    async def list_by_student(self, student_id: UUID) -> list[GuardianLink]:
        result = await self._db.execute(
            select(GuardianLinkModel)
            .where(
                GuardianLinkModel.student_id == str(student_id),
                GuardianLinkModel.status == "active",
            )
            .order_by(GuardianLinkModel.created_at.desc())
        )
        return [_to_link(m) for m in result.scalars().all()]

    async def update(self, link: GuardianLink) -> GuardianLink:
        result = await self._db.execute(
            select(GuardianLinkModel).where(GuardianLinkModel.id == str(link.id))
        )
        m = result.scalar_one()
        m.status = link.status
        await self._db.flush()
        await self._db.refresh(m)
        return _to_link(m)
