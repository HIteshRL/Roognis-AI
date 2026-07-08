from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.knowledge import Document, DocumentChunk, IngestionJob, KnowledgeBase
from src.domain.repositories.knowledge_repository import (
    AbstractChunkRepository,
    AbstractDocumentRepository,
    AbstractIngestionJobRepository,
    AbstractKnowledgeBaseRepository,
)
from src.infrastructure.database.models.knowledge import (
    DocumentChunkModel,
    DocumentModel,
    IngestionJobModel,
    KnowledgeBaseModel,
)

# ── Mappers ───────────────────────────────────────────────────────────────────

def _to_kb(m: KnowledgeBaseModel) -> KnowledgeBase:
    kb = KnowledgeBase.__new__(KnowledgeBase)
    kb.id = UUID(m.id)
    kb.name = m.name
    kb.description = m.description
    kb.institution = m.institution
    kb.subject = m.subject
    kb.grade = getattr(m, "grade", None)
    kb.chapter = getattr(m, "chapter", None)
    kb.topic = getattr(m, "topic", None)
    kb.language = m.language
    kb.is_active = m.is_active
    kb.created_by = UUID(m.created_by)
    kb.created_at = m.created_at
    kb.updated_at = m.updated_at
    return kb


def _to_doc(m: DocumentModel) -> Document:
    d = Document.__new__(Document)
    d.id = UUID(m.id)
    d.knowledge_base_id = UUID(m.knowledge_base_id)
    d.uploaded_by = UUID(m.uploaded_by)
    d.filename = m.filename
    d.title = m.title
    d.description = m.description
    d.file_type = m.file_type
    d.file_size = m.file_size
    d.storage_path = m.storage_path
    d.status = m.status
    d.chunk_count = m.chunk_count
    d.error_message = m.error_message
    d.metadata = m.extra_metadata or {}
    d.created_at = m.created_at
    d.updated_at = m.updated_at
    return d


def _to_chunk(m: DocumentChunkModel) -> DocumentChunk:
    c = DocumentChunk.__new__(DocumentChunk)
    c.id = UUID(m.id)
    c.document_id = UUID(m.document_id)
    c.knowledge_base_id = UUID(m.knowledge_base_id)
    c.content = m.content
    c.chunk_index = m.chunk_index
    c.vector_id = m.vector_id
    c.token_count = m.token_count
    c.page_number = m.page_number
    c.char_start = m.char_start
    c.char_end = m.char_end
    c.metadata = m.extra_metadata or {}
    c.created_at = m.created_at
    return c


def _to_job(m: IngestionJobModel) -> IngestionJob:
    j = IngestionJob.__new__(IngestionJob)
    j.id = UUID(m.id)
    j.document_id = UUID(m.document_id)
    j.status = m.status
    j.progress = m.progress
    j.error_message = m.error_message
    j.created_at = m.created_at
    j.updated_at = m.updated_at
    return j


# ── Knowledge Base Repository ─────────────────────────────────────────────────

class KnowledgeBaseRepository(AbstractKnowledgeBaseRepository):
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(self, kb: KnowledgeBase) -> KnowledgeBase:
        model = KnowledgeBaseModel(
            id=str(kb.id),
            name=kb.name,
            description=kb.description,
            institution=kb.institution,
            subject=kb.subject,
            grade=kb.grade,
            chapter=kb.chapter,
            topic=kb.topic,
            language=kb.language,
            is_active=kb.is_active,
            created_by=str(kb.created_by),
        )
        self._db.add(model)
        await self._db.flush()
        await self._db.refresh(model)
        return _to_kb(model)

    async def get_by_id(self, kb_id: UUID) -> KnowledgeBase | None:
        result = await self._db.execute(
            select(KnowledgeBaseModel).where(KnowledgeBaseModel.id == str(kb_id))
        )
        m = result.scalar_one_or_none()
        return _to_kb(m) if m else None

    async def list_all(self, page: int, limit: int) -> tuple[list[KnowledgeBase], int]:
        offset = (page - 1) * limit
        total = (await self._db.execute(select(func.count(KnowledgeBaseModel.id)))).scalar_one()
        result = await self._db.execute(
            select(KnowledgeBaseModel)
            .order_by(KnowledgeBaseModel.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return [_to_kb(m) for m in result.scalars().all()], total

    async def update(self, kb: KnowledgeBase) -> KnowledgeBase:
        result = await self._db.execute(
            select(KnowledgeBaseModel).where(KnowledgeBaseModel.id == str(kb.id))
        )
        model = result.scalar_one()
        model.name = kb.name
        model.description = kb.description
        model.institution = kb.institution
        model.subject = kb.subject
        model.grade = kb.grade
        model.chapter = kb.chapter
        model.topic = kb.topic
        model.language = kb.language
        model.is_active = kb.is_active
        await self._db.flush()
        await self._db.refresh(model)
        return _to_kb(model)

    async def delete(self, kb_id: UUID) -> None:
        result = await self._db.execute(
            select(KnowledgeBaseModel).where(KnowledgeBaseModel.id == str(kb_id))
        )
        m = result.scalar_one_or_none()
        if m:
            await self._db.delete(m)
            await self._db.flush()


# ── Document Repository ───────────────────────────────────────────────────────

class DocumentRepository(AbstractDocumentRepository):
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(self, document: Document) -> Document:
        model = DocumentModel(
            id=str(document.id),
            knowledge_base_id=str(document.knowledge_base_id),
            uploaded_by=str(document.uploaded_by),
            filename=document.filename,
            title=document.title,
            description=document.description,
            file_type=document.file_type,
            file_size=document.file_size,
            storage_path=document.storage_path,
            status=document.status,
            chunk_count=document.chunk_count,
            error_message=document.error_message,
            extra_metadata=document.metadata or None,
        )
        self._db.add(model)
        await self._db.flush()
        await self._db.refresh(model)
        return _to_doc(model)

    async def get_by_id(self, document_id: UUID) -> Document | None:
        result = await self._db.execute(
            select(DocumentModel).where(DocumentModel.id == str(document_id))
        )
        m = result.scalar_one_or_none()
        return _to_doc(m) if m else None

    async def list_by_knowledge_base(
        self, kb_id: UUID, page: int, limit: int
    ) -> tuple[list[Document], int]:
        offset = (page - 1) * limit
        total = (
            await self._db.execute(
                select(func.count(DocumentModel.id)).where(
                    DocumentModel.knowledge_base_id == str(kb_id)
                )
            )
        ).scalar_one()
        result = await self._db.execute(
            select(DocumentModel)
            .where(DocumentModel.knowledge_base_id == str(kb_id))
            .order_by(DocumentModel.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return [_to_doc(m) for m in result.scalars().all()], total

    async def update(self, document: Document) -> Document:
        result = await self._db.execute(
            select(DocumentModel).where(DocumentModel.id == str(document.id))
        )
        model = result.scalar_one()
        model.title = document.title
        model.description = document.description
        model.storage_path = document.storage_path
        model.status = document.status
        model.chunk_count = document.chunk_count
        model.error_message = document.error_message
        model.extra_metadata = document.metadata or None
        await self._db.flush()
        await self._db.refresh(model)
        return _to_doc(model)

    async def delete(self, document_id: UUID) -> None:
        result = await self._db.execute(
            select(DocumentModel).where(DocumentModel.id == str(document_id))
        )
        m = result.scalar_one_or_none()
        if m:
            await self._db.delete(m)
            await self._db.flush()


# ── Chunk Repository ──────────────────────────────────────────────────────────

class ChunkRepository(AbstractChunkRepository):
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create_many(self, chunks: list[DocumentChunk]) -> list[DocumentChunk]:
        models = [
            DocumentChunkModel(
                id=str(c.id),
                document_id=str(c.document_id),
                knowledge_base_id=str(c.knowledge_base_id),
                content=c.content,
                chunk_index=c.chunk_index,
                vector_id=c.vector_id,
                token_count=c.token_count,
                page_number=c.page_number,
                char_start=c.char_start,
                char_end=c.char_end,
                extra_metadata=c.metadata or None,
            )
            for c in chunks
        ]
        self._db.add_all(models)
        await self._db.flush()
        return [_to_chunk(m) for m in models]

    async def list_by_document(self, document_id: UUID) -> list[DocumentChunk]:
        result = await self._db.execute(
            select(DocumentChunkModel)
            .where(DocumentChunkModel.document_id == str(document_id))
            .order_by(DocumentChunkModel.chunk_index)
        )
        return [_to_chunk(m) for m in result.scalars().all()]

    async def delete_by_document(self, document_id: UUID) -> None:
        result = await self._db.execute(
            select(DocumentChunkModel).where(DocumentChunkModel.document_id == str(document_id))
        )
        for m in result.scalars().all():
            await self._db.delete(m)
        await self._db.flush()

    async def count_by_document(self, document_id: UUID) -> int:
        result = await self._db.execute(
            select(func.count(DocumentChunkModel.id)).where(
                DocumentChunkModel.document_id == str(document_id)
            )
        )
        return result.scalar_one()


# ── Ingestion Job Repository ──────────────────────────────────────────────────

class IngestionJobRepository(AbstractIngestionJobRepository):
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(self, job: IngestionJob) -> IngestionJob:
        model = IngestionJobModel(
            id=str(job.id),
            document_id=str(job.document_id),
            status=job.status,
            progress=job.progress,
        )
        self._db.add(model)
        await self._db.flush()
        await self._db.refresh(model)
        return _to_job(model)

    async def get_by_document_id(self, document_id: UUID) -> IngestionJob | None:
        result = await self._db.execute(
            select(IngestionJobModel).where(
                IngestionJobModel.document_id == str(document_id)
            )
        )
        m = result.scalar_one_or_none()
        return _to_job(m) if m else None

    async def update(self, job: IngestionJob) -> IngestionJob:
        result = await self._db.execute(
            select(IngestionJobModel).where(IngestionJobModel.id == str(job.id))
        )
        model = result.scalar_one()
        model.status = job.status
        model.progress = job.progress
        model.error_message = job.error_message
        await self._db.flush()
        await self._db.refresh(model)
        return _to_job(model)
