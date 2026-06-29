"""
Orchestrates the full document ingestion pipeline:
  upload → parse → chunk → embed → index → persist

Designed to run as a FastAPI BackgroundTask.
Each step updates the IngestionJob record so the frontend can poll progress.
"""
import structlog
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.chunking_service import ChunkingService
from src.application.services.vector_service import VectorService
from src.domain.entities.knowledge import DocumentChunk
from src.domain.repositories.knowledge_repository import (
    AbstractChunkRepository,
    AbstractDocumentRepository,
    AbstractIngestionJobRepository,
)
from src.infrastructure.database.repositories.knowledge_repository import (
    ChunkRepository,
    DocumentRepository,
    IngestionJobRepository,
)
from src.infrastructure.database.session import AsyncSessionLocal
from src.infrastructure.embeddings.base import AbstractEmbeddingProvider
from src.infrastructure.parsing.factory import get_parser
from src.infrastructure.vector.base import AbstractVectorStore

logger = structlog.get_logger(__name__)


class IngestionPipeline:
    def __init__(
        self,
        vector_store: AbstractVectorStore,
        embedding_provider: AbstractEmbeddingProvider,
        chunk_size: int = 512,
        chunk_overlap: int = 64,
        chunk_strategy: str = "fixed",
    ) -> None:
        self._vector_store = vector_store
        self._embedding_provider = embedding_provider
        self._chunking_svc = ChunkingService(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            strategy=chunk_strategy,  # type: ignore[arg-type]
        )
        self._vector_svc = VectorService(vector_store, embedding_provider)

    async def run(self, document_id: UUID, storage_path: str, file_type: str) -> None:
        """Entry point called by BackgroundTask. Opens its own DB session."""
        async with AsyncSessionLocal() as db:
            doc_repo = DocumentRepository(db)
            chunk_repo = ChunkRepository(db)
            job_repo = IngestionJobRepository(db)

            job = await job_repo.get_by_document_id(document_id)
            if not job:
                logger.error("ingestion_job_not_found", document_id=str(document_id))
                return

            doc = await doc_repo.get_by_id(document_id)
            if not doc:
                logger.error("ingestion_document_not_found", document_id=str(document_id))
                return

            try:
                # Step 1 — Parsing
                job.advance("parsing", 10)
                await job_repo.update(job)
                doc.mark_processing()
                await doc_repo.update(doc)
                await db.commit()

                parser = get_parser(storage_path, file_type)
                parsed = await parser.parse(storage_path)
                logger.info("document_parsed", pages=parsed.total_pages)

                # Step 2 — Chunking
                job.advance("chunking", 30)
                await job_repo.update(job)
                await db.commit()

                raw_chunks = self._chunking_svc.chunk_document(parsed, doc.metadata)
                logger.info("document_chunked", chunk_count=len(raw_chunks))

                # Step 3 — Build domain chunk entities
                domain_chunks = [
                    DocumentChunk(
                        document_id=document_id,
                        knowledge_base_id=doc.knowledge_base_id,
                        content=c.content,
                        chunk_index=c.chunk_index,
                        token_count=c.token_count,
                        page_number=c.page_number,
                        char_start=c.char_start,
                        char_end=c.char_end,
                        metadata=c.metadata,
                    )
                    for c in raw_chunks
                ]

                # Step 4 — Embedding + indexing
                job.advance("embedding", 50)
                await job_repo.update(job)
                await db.commit()

                indexed_chunks = await self._vector_svc.index_chunks(
                    domain_chunks, document_title=doc.title or doc.filename
                )

                # Step 5 — Persist chunks to PostgreSQL
                job.advance("indexing", 80)
                await job_repo.update(job)
                await db.commit()

                # Delete old chunks before re-indexing
                await chunk_repo.delete_by_document(document_id)
                await chunk_repo.create_many(indexed_chunks)

                # Step 6 — Mark complete
                doc.mark_ready(len(indexed_chunks))
                await doc_repo.update(doc)
                job.complete()
                await job_repo.update(job)
                await db.commit()

                logger.info(
                    "ingestion_complete",
                    document_id=str(document_id),
                    chunks=len(indexed_chunks),
                )

            except Exception as exc:
                logger.error("ingestion_failed", document_id=str(document_id), error=str(exc))
                try:
                    doc.mark_failed(str(exc))
                    await doc_repo.update(doc)
                    job.fail(str(exc))
                    await job_repo.update(job)
                    await db.commit()
                except Exception:
                    logger.error("ingestion_rollback_failed", exc_info=True)
