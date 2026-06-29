from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.entities.knowledge import Document, DocumentChunk, IngestionJob, KnowledgeBase


class AbstractKnowledgeBaseRepository(ABC):
    @abstractmethod
    async def create(self, kb: KnowledgeBase) -> KnowledgeBase: ...

    @abstractmethod
    async def get_by_id(self, kb_id: UUID) -> KnowledgeBase | None: ...

    @abstractmethod
    async def list_all(self, page: int, limit: int) -> tuple[list[KnowledgeBase], int]: ...

    @abstractmethod
    async def update(self, kb: KnowledgeBase) -> KnowledgeBase: ...

    @abstractmethod
    async def delete(self, kb_id: UUID) -> None: ...


class AbstractDocumentRepository(ABC):
    @abstractmethod
    async def create(self, document: Document) -> Document: ...

    @abstractmethod
    async def get_by_id(self, document_id: UUID) -> Document | None: ...

    @abstractmethod
    async def list_by_knowledge_base(
        self, kb_id: UUID, page: int, limit: int
    ) -> tuple[list[Document], int]: ...

    @abstractmethod
    async def update(self, document: Document) -> Document: ...

    @abstractmethod
    async def delete(self, document_id: UUID) -> None: ...


class AbstractChunkRepository(ABC):
    @abstractmethod
    async def create_many(self, chunks: list[DocumentChunk]) -> list[DocumentChunk]: ...

    @abstractmethod
    async def list_by_document(self, document_id: UUID) -> list[DocumentChunk]: ...

    @abstractmethod
    async def delete_by_document(self, document_id: UUID) -> None: ...

    @abstractmethod
    async def count_by_document(self, document_id: UUID) -> int: ...


class AbstractIngestionJobRepository(ABC):
    @abstractmethod
    async def create(self, job: IngestionJob) -> IngestionJob: ...

    @abstractmethod
    async def get_by_document_id(self, document_id: UUID) -> IngestionJob | None: ...

    @abstractmethod
    async def update(self, job: IngestionJob) -> IngestionJob: ...
