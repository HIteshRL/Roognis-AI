from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4


@dataclass
class KnowledgeBase:
    name: str
    created_by: UUID
    id: UUID = field(default_factory=uuid4)
    description: str | None = None
    institution: str | None = None
    subject: str | None = None
    language: str = "en"
    is_active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class Document:
    knowledge_base_id: UUID
    uploaded_by: UUID
    filename: str
    file_type: str
    file_size: int
    id: UUID = field(default_factory=uuid4)
    title: str | None = None
    description: str | None = None
    storage_path: str = ""
    status: str = "pending"        # pending | processing | ready | failed
    chunk_count: int = 0
    error_message: str | None = None
    metadata: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def mark_processing(self) -> None:
        self.status = "processing"
        self.updated_at = datetime.now(UTC)

    def mark_ready(self, chunk_count: int) -> None:
        self.status = "ready"
        self.chunk_count = chunk_count
        self.updated_at = datetime.now(UTC)

    def mark_failed(self, error: str) -> None:
        self.status = "failed"
        self.error_message = error
        self.updated_at = datetime.now(UTC)


@dataclass
class DocumentChunk:
    document_id: UUID
    knowledge_base_id: UUID
    content: str
    chunk_index: int
    id: UUID = field(default_factory=uuid4)
    vector_id: str = ""             # ID of the corresponding point in Qdrant
    token_count: int = 0
    page_number: int | None = None
    char_start: int = 0
    char_end: int = 0
    metadata: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class IngestionJob:
    document_id: UUID
    id: UUID = field(default_factory=uuid4)
    status: str = "queued"         # queued | parsing | chunking | embedding | indexing | done | failed
    progress: int = 0              # 0–100
    error_message: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def advance(self, status: str, progress: int) -> None:
        self.status = status
        self.progress = progress
        self.updated_at = datetime.now(UTC)

    def fail(self, error: str) -> None:
        self.status = "failed"
        self.error_message = error
        self.updated_at = datetime.now(UTC)

    def complete(self) -> None:
        self.status = "done"
        self.progress = 100
        self.updated_at = datetime.now(UTC)
