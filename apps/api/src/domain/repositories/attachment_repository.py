from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.entities.attachment import MessageAttachment


class AbstractMessageAttachmentRepository(ABC):
    @abstractmethod
    async def create(self, attachment: MessageAttachment) -> MessageAttachment: ...

    @abstractmethod
    async def get_by_id(self, attachment_id: UUID) -> MessageAttachment | None: ...

    @abstractmethod
    async def list_by_ids(
        self, attachment_ids: list[UUID], user_id: UUID
    ) -> list[MessageAttachment]: ...

    @abstractmethod
    async def list_by_message(self, message_id: UUID) -> list[MessageAttachment]: ...

    @abstractmethod
    async def list_by_messages(
        self, message_ids: list[UUID]
    ) -> list[MessageAttachment]: ...

    @abstractmethod
    async def link_to_message(
        self, attachment_ids: list[UUID], message_id: UUID
    ) -> None: ...
