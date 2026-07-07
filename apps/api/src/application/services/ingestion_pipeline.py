"""
Orchestrates the full document ingestion pipeline:
  upload → parse → chunk → embed → index → persist

Designed to run as a FastAPI BackgroundTask.
Each step updates the IngestionJob record so the frontend can poll progress.
"""
from uuid import UUID

import structlog

from src.application.services.chunking_service import ChunkingService
from src.application.services.vector_service import VectorService
from src.domain.entities.knowledge import DocumentChunk
from src.infrastructure.database.repositories.knowledge_repository import (
    ChunkRepository,
    DocumentRepository,
    IngestionJobRepository,
    KnowledgeBaseRepository,
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
        chunk_target_tokens: int = 350,
        chunk_min_tokens: int = 128,
        chunk_safety_ratio: float = 1.15,
        chunk_semantic_threshold: float = 0.82,
        chunk_semantic_enabled: bool = True,
    ) -> None:
        self._vector_store = vector_store
        self._embedding_provider = embedding_provider
        self._chunking_svc = ChunkingService(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            strategy=chunk_strategy,  # type: ignore[arg-type]
            embedder=embedding_provider,
            target_tokens=chunk_target_tokens,
            min_tokens=chunk_min_tokens,
            safety_ratio=chunk_safety_ratio,
            semantic_threshold=chunk_semantic_threshold,
            semantic_enabled=chunk_semantic_enabled,
        )
        self._vector_svc = VectorService(vector_store, embedding_provider)

    async def run(self, document_id: UUID, storage_path: str, file_type: str) -> None:
        """Entry point called by BackgroundTask. Opens its own DB session."""
        async with AsyncSessionLocal() as db:
            doc_repo = DocumentRepository(db)
            chunk_repo = ChunkRepository(db)
            job_repo = IngestionJobRepository(db)
            kb_repo = KnowledgeBaseRepository(db)

            job = await job_repo.get_by_document_id(document_id)
            if not job:
                logger.error("ingestion_job_not_found", document_id=str(document_id))
                return

            doc = await doc_repo.get_by_id(document_id)
            if not doc:
                logger.error("ingestion_document_not_found", document_id=str(document_id))
                return

            # Fetch KB to propagate academic metadata into vector payloads
            kb = await kb_repo.get_by_id(doc.knowledge_base_id)
            academic_meta: dict = {}
            if kb:
                for field in ("institution", "grade", "subject", "chapter", "topic"):
                    val = getattr(kb, field, None)
                    if val:
                        academic_meta[field] = val

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

                # Adaptive/semantic chunking is async (may embed atoms to find
                # topic boundaries); fixed/sliding stay synchronous.
                if self._chunking_svc.is_adaptive:
                    raw_chunks = await self._chunking_svc.chunk_document_adaptive(
                        parsed, doc.metadata
                    )
                else:
                    raw_chunks = self._chunking_svc.chunk_document(parsed, doc.metadata)
                logger.info(
                    "document_chunked",
                    chunk_count=len(raw_chunks),
                    strategy=self._chunking_svc.strategy,
                )

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

                # Purge any previous vectors for this document first — chunks
                # get fresh UUIDs on every run, so without this a reindex
                # would leave stale duplicate points in Qdrant. No-op on
                # first-time ingestion.
                await self._vector_svc.delete_document_vectors(str(document_id))

                indexed_chunks = await self._vector_svc.index_chunks(
                    domain_chunks,
                    document_title=doc.title or doc.filename,
                    academic_meta=academic_meta,
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
