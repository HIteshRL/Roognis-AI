from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.conversation import Conversation, Message
from src.domain.repositories.conversation_repository import (
    AbstractConversationRepository,
    AbstractMessageRepository,
)
from src.infrastructure.database.models.conversation import ConversationModel, MessageModel


def _to_conversation(m: ConversationModel) -> Conversation:
    c = Conversation.__new__(Conversation)
    c.id = UUID(m.id)
    c.user_id = UUID(m.user_id)
    c.title = m.title
    c.subject = m.subject
    c.chapter = m.chapter
    c.is_archived = m.is_archived
    c.created_at = m.created_at
    c.updated_at = m.updated_at
    return c


def _to_message(m: MessageModel) -> Message:
    msg = Message.__new__(Message)
    msg.id = UUID(m.id)
    msg.conversation_id = UUID(m.conversation_id)
    msg.role = m.role
    msg.content = m.content
    msg.token_count = m.token_count
    msg.created_at = m.created_at
    return msg


class ConversationRepository(AbstractConversationRepository):
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(self, conversation: Conversation) -> Conversation:
        model = ConversationModel(
            id=str(conversation.id),
            user_id=str(conversation.user_id),
            title=conversation.title,
            subject=conversation.subject,
            chapter=conversation.chapter,
            is_archived=conversation.is_archived,
        )
        self._db.add(model)
        await self._db.flush()
        await self._db.refresh(model)
        return _to_conversation(model)

    async def get_by_id(self, conversation_id: UUID) -> Conversation | None:
        result = await self._db.execute(
            select(ConversationModel).where(ConversationModel.id == str(conversation_id))
        )
        model = result.scalar_one_or_none()
        return _to_conversation(model) if model else None

    async def list_by_user(
        self, user_id: UUID, page: int, limit: int,
        subject: str | None = None, chapter: str | None = None,
    ) -> tuple[list[Conversation], int]:
        offset = (page - 1) * limit

        filters = [
            ConversationModel.user_id == str(user_id),
            ConversationModel.is_archived == False,  # noqa: E712
        ]
        if subject is not None:
            if subject == "":
                filters.append(ConversationModel.subject.is_(None))
            else:
                filters.append(ConversationModel.subject == subject)
        if chapter:
            filters.append(ConversationModel.chapter == chapter)

        total_result = await self._db.execute(
            select(func.count()).select_from(ConversationModel).where(*filters)
        )
        total = total_result.scalar_one()

        result = await self._db.execute(
            select(ConversationModel)
            .where(*filters)
            .order_by(ConversationModel.updated_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return [_to_conversation(m) for m in result.scalars().all()], total

    async def subject_counts(self, user_id: UUID) -> list[tuple[str | None, int]]:
        result = await self._db.execute(
            select(ConversationModel.subject, func.count())
            .where(
                ConversationModel.user_id == str(user_id),
                ConversationModel.is_archived == False,  # noqa: E712
            )
            .group_by(ConversationModel.subject)
        )
        return list(result.all())

    async def chapter_counts(
        self, user_id: UUID, subject: str
    ) -> list[tuple[str | None, int]]:
        result = await self._db.execute(
            select(ConversationModel.chapter, func.count())
            .where(
                ConversationModel.user_id == str(user_id),
                ConversationModel.subject == subject,
                ConversationModel.chapter.is_not(None),
                ConversationModel.is_archived == False,  # noqa: E712
            )
            .group_by(ConversationModel.chapter)
        )
        return list(result.all())

    async def update(self, conversation: Conversation) -> Conversation:
        result = await self._db.execute(
            select(ConversationModel).where(ConversationModel.id == str(conversation.id))
        )
        model = result.scalar_one()
        model.title = conversation.title
        model.subject = conversation.subject
        model.chapter = conversation.chapter
        model.is_archived = conversation.is_archived
        await self._db.flush()
        await self._db.refresh(model)
        return _to_conversation(model)

    async def delete(self, conversation_id: UUID) -> None:
        result = await self._db.execute(
            select(ConversationModel).where(ConversationModel.id == str(conversation_id))
        )
        model = result.scalar_one_or_none()
        if model:
            await self._db.delete(model)
            await self._db.flush()


class MessageRepository(AbstractMessageRepository):
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(self, message: Message) -> Message:
        model = MessageModel(
            id=str(message.id),
            conversation_id=str(message.conversation_id),
            role=message.role,
            content=message.content,
            token_count=message.token_count,
        )
        self._db.add(model)
        await self._db.flush()
        await self._db.refresh(model)
        return _to_message(model)

    async def get_by_id(self, message_id: UUID) -> Message | None:
        result = await self._db.execute(
            select(MessageModel).where(MessageModel.id == str(message_id))
        )
        model = result.scalar_one_or_none()
        return _to_message(model) if model else None

    async def list_by_conversation(
        self, conversation_id: UUID, limit: int | None = None
    ) -> list[Message]:
        query = (
            select(MessageModel)
            .where(MessageModel.conversation_id == str(conversation_id))
            .order_by(MessageModel.created_at.asc())
        )
        if limit:
            query = query.limit(limit)
        result = await self._db.execute(query)
        return [_to_message(m) for m in result.scalars().all()]

    async def count_by_conversation(self, conversation_id: UUID) -> int:
        result = await self._db.execute(
            select(func.count()).where(
                MessageModel.conversation_id == str(conversation_id)
            )
        )
        return result.scalar_one()
