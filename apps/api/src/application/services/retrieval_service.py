import time

import structlog

from src.application.dtos.knowledge import RetrievedContext, SearchResultItem
from src.infrastructure.embeddings.base import AbstractEmbeddingProvider
from src.infrastructure.vector.base import AbstractVectorStore, SearchResult

logger = structlog.get_logger(__name__)

_MIN_CONTEXT_CHUNKS = 1
_MAX_PER_DOCUMENT = 2


class RetrievalService:
    """
    Converts a user query into a ranked list of relevant document chunks.
    Supports strict curriculum filtering: institution / grade / subject / chapter / topic.
    Never touches LLM — pure similarity search + ranking.

    v0.2 CAG: retrieve_contextual() adds query enrichment, cascading scope
    broadening, and single-embed multi-search for context-aware generation.
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
        k = top_k or self._top_k
        threshold = score_threshold or self._threshold

        t0 = time.monotonic()
        query_vector = await self._embedder.embed_query(query)
        embedding_ms = (time.monotonic() - t0) * 1000

        filter_payload: dict[str, str] = {}
        if knowledge_base_id:
            filter_payload["knowledge_base_id"] = knowledge_base_id
        if curriculum_filter:
            filter_payload.update(curriculum_filter)

        t1 = time.monotonic()
        results = await self._store.search(
            query_vector=query_vector,
            top_k=k,
            score_threshold=threshold,
            filter_payload=filter_payload or None,
        )
        retrieval_ms = (time.monotonic() - t1) * 1000

        items = self._results_to_items(results)
        deduped = self._deduplicate(items)

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

    # ── CAG: Context-Aware Generation ────────────────────────────────────────

    async def retrieve_contextual(
        self,
        query: str,
        subject: str | None = None,
        chapter: str | None = None,
        grade: str | None = None,
        knowledge_base_id: str | None = None,
        top_k: int | None = None,
        score_threshold: float | None = None,
    ) -> tuple[RetrievedContext, dict]:
        """
        Context-aware retrieval: enriches the query with curriculum scope,
        embeds once, then cascades through progressively broader filters
        until sufficient context is found.

        Cascade levels: exact (subject+chapter) → subject → grade → unscoped.
        """
        k = top_k or self._top_k
        threshold = score_threshold or self._threshold

        enriched = self._enrich_query(query, subject, chapter)

        t0 = time.monotonic()
        query_vector = await self._embedder.embed_query(enriched)
        embedding_ms = (time.monotonic() - t0) * 1000

        cascade = self._build_cascade(subject, chapter, grade, knowledge_base_id)

        best_context: RetrievedContext | None = None
        best_level = "unscoped"
        total_retrieval_ms = 0.0

        for level_name, filter_payload in cascade:
            t1 = time.monotonic()
            results = await self._store.search(
                query_vector=query_vector,
                top_k=k,
                score_threshold=threshold,
                filter_payload=filter_payload,
            )
            total_retrieval_ms += (time.monotonic() - t1) * 1000

            items = self._results_to_items(results)
            deduped = self._deduplicate(items)

            context = RetrievedContext(
                chunks=deduped,
                has_context=bool(deduped),
                query=query,
            )

            if len(deduped) >= _MIN_CONTEXT_CHUNKS:
                logger.info(
                    "cag_resolved",
                    level=level_name,
                    chunks=len(deduped),
                    scores=[round(c.score, 3) for c in deduped],
                    query_len=len(query),
                )
                return context, {
                    "embedding_ms": embedding_ms,
                    "retrieval_ms": total_retrieval_ms,
                    "cascade_level": level_name,
                }

            if best_context is None or len(deduped) > len(best_context.chunks):
                best_context = context
                best_level = level_name

            logger.info("cag_broadening", from_level=level_name, chunks=len(deduped))

        final = best_context or RetrievedContext(chunks=[], has_context=False, query=query)
        logger.info("cag_exhausted", chunks=len(final.chunks), levels_tried=len(cascade))
        return final, {
            "embedding_ms": embedding_ms,
            "retrieval_ms": total_retrieval_ms,
            "cascade_level": best_level,
        }

    # ── Helpers ──────────────────────────────────────────────────────────────

    @staticmethod
    def _enrich_query(query: str, subject: str | None, chapter: str | None) -> str:
        if not subject:
            return query
        prefix = subject
        if chapter:
            prefix = f"{subject} — {chapter}"
        return f"[{prefix}] {query}"

    @staticmethod
    def _build_cascade(
        subject: str | None,
        chapter: str | None,
        grade: str | None,
        knowledge_base_id: str | None,
    ) -> list[tuple[str, dict[str, str] | None]]:
        levels: list[tuple[str, dict[str, str] | None]] = []

        if subject and chapter:
            f: dict[str, str] = {"subject": subject, "chapter": chapter}
            if grade:
                f["grade"] = grade
            if knowledge_base_id:
                f["knowledge_base_id"] = knowledge_base_id
            levels.append(("exact", f))

        if subject:
            f = {"subject": subject}
            if grade:
                f["grade"] = grade
            if knowledge_base_id:
                f["knowledge_base_id"] = knowledge_base_id
            if not levels or levels[-1][1] != f:
                levels.append(("subject", f))

        if grade:
            f = {"grade": grade}
            if knowledge_base_id:
                f["knowledge_base_id"] = knowledge_base_id
            levels.append(("grade", f))

        levels.append(("unscoped", None))
        return levels

    @staticmethod
    def _results_to_items(results: list[SearchResult]) -> list[SearchResultItem]:
        return [
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
                    if fk
                    not in {"content", "document_id", "document_title", "knowledge_base_id"}
                },
            )
            for r in results
        ]

    @staticmethod
    def _deduplicate(
        items: list[SearchResultItem],
        max_per_doc: int = _MAX_PER_DOCUMENT,
    ) -> list[SearchResultItem]:
        doc_counts: dict[str, int] = {}
        deduped: list[SearchResultItem] = []
        for item in sorted(items, key=lambda x: x.score, reverse=True):
            count = doc_counts.get(item.document_id, 0)
            if count < max_per_doc:
                deduped.append(item)
                doc_counts[item.document_id] = count + 1
        return deduped
