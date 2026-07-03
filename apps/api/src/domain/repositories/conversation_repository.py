from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.entities.conversation import Conversation, Message


class AbstractConversationRepository(ABC):
    @abstractmethod
    async def create(self, conversation: Conversation) -> Conversation: ...

    @abstractmethod
    async def get_by_id(self, conversation_id: UUID) -> Conversation | None: ...

    @abstractmethod
    async def list_by_user(
        self, user_id: UUID, page: int, limit: int,
        subject: str | None = None, chapter: str | None = None,
    ) -> tuple[list[Conversation], int]: ...

    @abstractmethod
    async def subject_counts(self, user_id: UUID) -> list[tuple[str | None, int]]: ...

    @abstractmethod
    async def chapter_counts(
        self, user_id: UUID, subject: str
    ) -> list[tuple[str | None, int]]: ...

    @abstractmethod
    async def update(self, conversation: Conversation) -> Conversation: ...

    @abstractmethod
    async def delete(self, conversation_id: UUID) -> None: ...


class AbstractMessageRepository(ABC):
    @abstractmethod
    async def create(self, message: Message) -> Message: ...

    @abstractmethod
    async def get_by_id(self, message_id: UUID) -> Message | None: ...

    @abstractmethod
    async def list_by_conversation(
        self, conversation_id: UUID, limit: int | None = None
    ) -> list[Message]: ...

    @abstractmethod
    async def count_by_conversation(self, conversation_id: UUID) -> int: ...
