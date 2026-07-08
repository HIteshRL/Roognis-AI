from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.media_job import MediaJob
from src.domain.repositories.media_job_repository import AbstractMediaJobRepository
from src.infrastructure.database.models.media_job import MediaJobModel


def _to_job(m: MediaJobModel) -> MediaJob:
    j = MediaJob.__new__(MediaJob)
    j.id = UUID(m.id)
    j.user_id = UUID(m.user_id)
    j.conversation_id = UUID(m.conversation_id) if m.conversation_id else None
    j.message_id = UUID(m.message_id)
    j.kind = m.kind
    j.status = m.status
    j.prompt = m.prompt
    j.attachment_id = UUID(m.attachment_id) if m.attachment_id else None
    j.progress = m.progress
    j.error_message = m.error_message
    j.created_at = m.created_at
    j.updated_at = m.updated_at
    return j


class MediaJobRepository(AbstractMediaJobRepository):
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(self, job: MediaJob) -> MediaJob:
        model = MediaJobModel(
            id=str(job.id),
            user_id=str(job.user_id),
            conversation_id=str(job.conversation_id) if job.conversation_id else None,
            message_id=str(job.message_id),
            kind=job.kind,
            status=job.status,
            prompt=job.prompt,
            attachment_id=str(job.attachment_id) if job.attachment_id else None,
            progress=job.progress,
            error_message=job.error_message,
        )
        self._db.add(model)
        await self._db.flush()
        await self._db.refresh(model)
        return _to_job(model)

    async def get_by_id(self, job_id: UUID) -> MediaJob | None:
        result = await self._db.execute(
            select(MediaJobModel).where(MediaJobModel.id == str(job_id))
        )
        model = result.scalar_one_or_none()
        return _to_job(model) if model else None

    async def update(self, job: MediaJob) -> MediaJob:
        result = await self._db.execute(
            select(MediaJobModel).where(MediaJobModel.id == str(job.id))
        )
        model = result.scalar_one()
        model.status = job.status
        model.progress = job.progress
        model.attachment_id = str(job.attachment_id) if job.attachment_id else None
        model.error_message = job.error_message
        await self._db.flush()
        await self._db.refresh(model)
        return _to_job(model)

    async def list_by_message(self, message_id: UUID) -> list[MediaJob]:
        result = await self._db.execute(
            select(MediaJobModel)
            .where(MediaJobModel.message_id == str(message_id))
            .order_by(MediaJobModel.created_at.desc())
        )
        return [_to_job(m) for m in result.scalars().all()]
