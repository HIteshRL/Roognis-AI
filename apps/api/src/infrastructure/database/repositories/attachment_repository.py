from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.attachment import MessageAttachment
from src.domain.repositories.attachment_repository import (
    AbstractMessageAttachmentRepository,
)
from src.infrastructure.database.models.attachment import MessageAttachmentModel


def _to_attachment(m: MessageAttachmentModel) -> MessageAttachment:
    a = MessageAttachment.__new__(MessageAttachment)
    a.id = UUID(m.id)
    a.user_id = UUID(m.user_id)
    a.message_id = UUID(m.message_id) if m.message_id else None
    a.kind = m.kind
    a.storage_path = m.storage_path
    a.content_type = m.content_type
    a.file_size = m.file_size
    a.width = m.width
    a.height = m.height
    a.created_at = m.created_at
    return a


class MessageAttachmentRepository(AbstractMessageAttachmentRepository):
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(self, attachment: MessageAttachment) -> MessageAttachment:
        model = MessageAttachmentModel(
            id=str(attachment.id),
            user_id=str(attachment.user_id),
            message_id=str(attachment.message_id) if attachment.message_id else None,
            kind=attachment.kind,
            storage_path=attachment.storage_path,
            content_type=attachment.content_type,
            file_size=attachment.file_size,
            width=attachment.width,
            height=attachment.height,
        )
        self._db.add(model)
        await self._db.flush()
        await self._db.refresh(model)
        return _to_attachment(model)

    async def get_by_id(self, attachment_id: UUID) -> MessageAttachment | None:
        result = await self._db.execute(
            select(MessageAttachmentModel).where(
                MessageAttachmentModel.id == str(attachment_id)
            )
        )
        model = result.scalar_one_or_none()
        return _to_attachment(model) if model else None

    async def list_by_ids(
        self, attachment_ids: list[UUID], user_id: UUID
    ) -> list[MessageAttachment]:
        if not attachment_ids:
            return []
        result = await self._db.execute(
            select(MessageAttachmentModel).where(
                MessageAttachmentModel.id.in_([str(a) for a in attachment_ids]),
                MessageAttachmentModel.user_id == str(user_id),
            )
        )
        return [_to_attachment(m) for m in result.scalars().all()]

    async def list_by_message(self, message_id: UUID) -> list[MessageAttachment]:
        result = await self._db.execute(
            select(MessageAttachmentModel)
            .where(MessageAttachmentModel.message_id == str(message_id))
            .order_by(MessageAttachmentModel.created_at.asc())
        )
        return [_to_attachment(m) for m in result.scalars().all()]

    async def list_by_messages(
        self, message_ids: list[UUID]
    ) -> list[MessageAttachment]:
        if not message_ids:
            return []
        result = await self._db.execute(
            select(MessageAttachmentModel)
            .where(MessageAttachmentModel.message_id.in_([str(m) for m in message_ids]))
            .order_by(MessageAttachmentModel.created_at.asc())
        )
        return [_to_attachment(m) for m in result.scalars().all()]

    async def link_to_message(
        self, attachment_ids: list[UUID], message_id: UUID
    ) -> None:
        if not attachment_ids:
            return
        await self._db.execute(
            update(MessageAttachmentModel)
            .where(MessageAttachmentModel.id.in_([str(a) for a in attachment_ids]))
            .values(message_id=str(message_id))
        )
        await self._db.flush()
