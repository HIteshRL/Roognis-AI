import time

import structlog

from src.application.dtos.knowledge import RetrievedContext, SearchResultItem
from src.infrastructure.embeddings.base import AbstractEmbeddingProvider
from src.infrastructure.vector.base import AbstractVectorStore

logger = structlog.get_logger(__name__)


class RetrievalService:
    """
    Converts a user query into a ranked list of relevant document chunks.
    Supports strict curriculum filtering: institution / grade / subject / chapter / topic.
    Never touches LLM — pure similarity search + ranking.
    """

    def __init__(
        self,
        vector_store: AbstractVectorStore,
        embedding_provider: AbstractEmbeddingProvider,
        top_k: int = 5,
        score_threshold: float = 0.35,
    ) -> None:
        self._store = vector_store
        self._embedder = embedding_provider
        self._top_k = top_k
        self._threshold = score_threshold

    async def retrieve(
        self,
        query: str,
        knowledge_base_id: str | None = None,
        curriculum_filter: dict[str, str] | None = None,
        top_k: int | None = None,
        score_threshold: float | None = None,
    ) -> tuple[RetrievedContext, dict[str, float]]:
        """
        Returns (RetrievedContext, timing) where timing has keys:
          embedding_ms, retrieval_ms
        """
        k = top_k or self._top_k
        threshold = score_threshold or self._threshold

        # ── Embed query ───────────────────────────────────────────────────────
        t0 = time.monotonic()
        query_vector = await self._embedder.embed_query(query)
        embedding_ms = (time.monotonic() - t0) * 1000

        # ── Build filter ──────────────────────────────────────────────────────
        filter_payload: dict[str, str] = {}
        if knowledge_base_id:
            filter_payload["knowledge_base_id"] = knowledge_base_id
        if curriculum_filter:
            filter_payload.update(curriculum_filter)

        # ── Vector search ─────────────────────────────────────────────────────
        t1 = time.monotonic()
        results = await self._store.search(
            query_vector=query_vector,
            top_k=k,
            score_threshold=threshold,
            filter_payload=filter_payload or None,
        )
        retrieval_ms = (time.monotonic() - t1) * 1000

        items = [
            SearchResultItem(
                chunk_id=r.id,
                document_id=r.payload.get("document_id", ""),
                document_title=r.payload.get("document_title"),
                content=r.payload.get("content", ""),
                score=r.score,
                page_number=r.payload.get("page_number"),
                metadata={
                    fk: fv
                    for fk, fv in r.payload.items()
                    if fk not in {"content", "document_id", "document_title", "knowledge_base_id"}
                },
            )
            for r in results
        ]

        # Keep highest-scoring chunk per document, but allow up to 2 per doc
        seen_docs: set[str] = set()
        deduped: list[SearchResultItem] = []
        for item in sorted(items, key=lambda x: x.score, reverse=True):
            if item.document_id not in seen_docs or len(deduped) < 2:
                deduped.append(item)
                seen_docs.add(item.document_id)

        logger.info(
            "retrieval_complete",
            query_len=len(query),
            raw_results=len(results),
            deduped_results=len(deduped),
            curriculum_filter=filter_payload,
            embedding_ms=round(embedding_ms, 1),
            retrieval_ms=round(retrieval_ms, 1),
            scores=[round(r.score, 3) for r in deduped],
            has_context=bool(deduped),
        )

        context = RetrievedContext(
            chunks=deduped,
            has_context=bool(deduped),
            query=query,
        )
        timing = {"embedding_ms": embedding_ms, "retrieval_ms": retrieval_ms}
        return context, timing
