import os
from uuid import UUID

import structlog

from src.application.dtos.knowledge import (
    ChunkResponse,
    DocumentResponse,
    DocumentUploadResponse,
    IngestionJobResponse,
)
from src.application.services.vector_service import VectorService
from src.config import Settings
from src.domain.entities.knowledge import Document, IngestionJob
from src.domain.exceptions import AuthorizationError, EntityNotFound, ValidationError
from src.domain.repositories.knowledge_repository import (
    AbstractChunkRepository,
    AbstractDocumentRepository,
    AbstractIngestionJobRepository,
    AbstractKnowledgeBaseRepository,
)
from src.infrastructure.parsing.factory import SUPPORTED_EXTENSIONS
from src.infrastructure.storage.base import AbstractFileStorage

logger = structlog.get_logger(__name__)


class DocumentService:
    def __init__(
        self,
        kb_repo: AbstractKnowledgeBaseRepository,
        doc_repo: AbstractDocumentRepository,
        chunk_repo: AbstractChunkRepository,
        job_repo: AbstractIngestionJobRepository,
        storage: AbstractFileStorage,
        vector_svc: VectorService,
        settings: Settings,
    ) -> None:
        self._kbs = kb_repo
        self._docs = doc_repo
        self._chunks = chunk_repo
        self._jobs = job_repo
        self._storage = storage
        self._vectors = vector_svc
        self._settings = settings

    async def upload(
        self,
        kb_id: UUID,
        user_id: UUID,
        filename: str,
        file_bytes: bytes,
        content_type: str,
        title: str | None = None,
        description: str | None = None,
    ) -> tuple[Document, IngestionJob]:
        ext = os.path.splitext(filename)[1].lower()
        if ext not in SUPPORTED_EXTENSIONS:
            raise ValidationError(
                f"Unsupported file type: {ext}. Supported: {SUPPORTED_EXTENSIONS}"
            )
        if len(file_bytes) > self._settings.max_upload_size_bytes:
            raise ValidationError(
                f"File too large. Maximum: {self._settings.max_upload_size_mb} MB"
            )

        kb = await self._kbs.get_by_id(kb_id)
        if not kb:
            raise EntityNotFound("Knowledge base not found")

        doc = Document(
            knowledge_base_id=kb_id,
            uploaded_by=user_id,
            filename=filename,
            file_type=content_type or ext,
            file_size=len(file_bytes),
            title=title or os.path.splitext(filename)[0],
            description=description,
        )
        doc = await self._docs.create(doc)

        storage_path = await self._storage.save(
            file_bytes, f"{kb_id}/{doc.id}{ext}"
        )
        doc.storage_path = storage_path
        doc = await self._docs.update(doc)

        job = IngestionJob(document_id=doc.id)
        job = await self._jobs.create(job)

        return doc, job

    async def get_document(self, document_id: UUID, user_id: UUID | None = None) -> Document:
        doc = await self._docs.get_by_id(document_id)
        if not doc:
            raise EntityNotFound("Document not found")
        return doc

    async def list_documents(
        self, kb_id: UUID, page: int, limit: int
    ) -> tuple[list[Document], int]:
        return await self._docs.list_by_knowledge_base(kb_id, page, limit)

    async def delete_document(self, document_id: UUID, user_id: UUID) -> None:
        doc = await self._docs.get_by_id(document_id)
        if not doc:
            raise EntityNotFound("Document not found")
        await self._vectors.delete_document_vectors(str(document_id))
        await self._chunks.delete_by_document(document_id)
        if doc.storage_path:
            await self._storage.delete(doc.storage_path)
        await self._docs.delete(document_id)

    async def get_chunks(self, document_id: UUID) -> list[ChunkResponse]:
        doc = await self._docs.get_by_id(document_id)
        if not doc:
            raise EntityNotFound("Document not found")
        chunks = await self._chunks.list_by_document(document_id)
        return [
            ChunkResponse(
                id=str(c.id),
                document_id=str(c.document_id),
                chunk_index=c.chunk_index,
                content=c.content,
                token_count=c.token_count,
                page_number=c.page_number,
                metadata=c.metadata,
            )
            for c in chunks
        ]

    async def get_job_status(self, document_id: UUID) -> IngestionJobResponse:
        job = await self._jobs.get_by_document_id(document_id)
        if not job:
            raise EntityNotFound("Ingestion job not found")
        return IngestionJobResponse(
            id=str(job.id),
            document_id=str(job.document_id),
            status=job.status,
            progress=job.progress,
            error_message=job.error_message,
            created_at=job.created_at.isoformat(),
            updated_at=job.updated_at.isoformat(),
        )

    @staticmethod
    def _to_response(doc: Document) -> DocumentResponse:
        return DocumentResponse(
            id=str(doc.id),
            knowledge_base_id=str(doc.knowledge_base_id),
            filename=doc.filename,
            title=doc.title,
            description=doc.description,
            file_type=doc.file_type,
            file_size=doc.file_size,
            status=doc.status,
            chunk_count=doc.chunk_count,
            error_message=doc.error_message,
            created_at=doc.created_at.isoformat(),
            updated_at=doc.updated_at.isoformat(),
        )
