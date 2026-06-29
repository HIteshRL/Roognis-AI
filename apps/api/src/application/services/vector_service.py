import structlog

from src.domain.entities.knowledge import DocumentChunk
from src.infrastructure.embeddings.base import AbstractEmbeddingProvider
from src.infrastructure.vector.base import AbstractVectorStore, VectorPoint

logger = structlog.get_logger(__name__)

_BATCH_SIZE = 32


class VectorService:
    """
    Manages the lifecycle of vectors in the vector store.
    Ensures the collection exists before any write operation.
    """

    def __init__(
        self,
        vector_store: AbstractVectorStore,
        embedding_provider: AbstractEmbeddingProvider,
    ) -> None:
        self._store = vector_store
        self._embedder = embedding_provider
        self._collection_ready = False

    async def _ensure_collection(self) -> None:
        if not self._collection_ready:
            await self._store.ensure_collection(self._embedder.dimension)
            self._collection_ready = True

    async def index_chunks(
        self, chunks: list[DocumentChunk], document_title: str | None = None
    ) -> list[DocumentChunk]:
        """Embed and index chunks. Returns chunks with vector_id populated."""
        await self._ensure_collection()

        indexed: list[DocumentChunk] = []
        for i in range(0, len(chunks), _BATCH_SIZE):
            batch = chunks[i : i + _BATCH_SIZE]
            texts = [c.content for c in batch]
            result = await self._embedder.embed(texts)

            points = [
                VectorPoint(
                    id=str(chunk.id),
                    vector=vector,
                    payload={
                        "chunk_id": str(chunk.id),
                        "document_id": str(chunk.document_id),
                        "knowledge_base_id": str(chunk.knowledge_base_id),
                        "document_title": document_title,
                        "content": chunk.content,
                        "chunk_index": chunk.chunk_index,
                        "page_number": chunk.page_number,
                        "token_count": chunk.token_count,
                        **chunk.metadata,
                    },
                )
                for chunk, vector in zip(batch, result.vectors)
            ]
            await self._store.upsert(points)

            for chunk in batch:
                chunk.vector_id = str(chunk.id)
            indexed.extend(batch)

            logger.info(
                "chunks_indexed",
                batch_start=i,
                batch_size=len(batch),
                total=len(chunks),
            )

        return indexed

    async def delete_document_vectors(self, document_id: str) -> None:
        await self._ensure_collection()
        await self._store.delete_by_payload({"document_id": document_id})

    async def collection_stats(self) -> dict:
        await self._ensure_collection()
        return await self._store.collection_stats()
