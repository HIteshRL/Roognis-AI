import re
import time

import structlog

from src.application.dtos.knowledge import RetrievedContext, SearchResultItem
from src.infrastructure.embeddings.base import AbstractEmbeddingProvider
from src.infrastructure.vector.base import AbstractVectorStore, SearchResult

logger = structlog.get_logger(__name__)

_MIN_CONTEXT_CHUNKS = 1
_MAX_PER_DOCUMENT = 2

_TOKEN_RE = re.compile(r"[a-z0-9]+")
_STOPWORDS = frozenset(
    "the a an of to in on at is are was were be been and or for with as by from "
    "what how why when where which who whom this that these those it its do does "
    "can could would should i you he she they we my your explain tell me about".split()
)


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
        rerank_enabled: bool = True,
        rerank_pool: int = 20,
        lexical_weight: float = 0.25,
    ) -> None:
        self._store = vector_store
        self._embedder = embedding_provider
        self._top_k = top_k
        self._threshold = score_threshold
        self._rerank_enabled = rerank_enabled
        self._rerank_pool = rerank_pool
        self._lexical_weight = lexical_weight

    def _fetch_k(self, k: int) -> int:
        """Fetch a wider candidate pool when re-ranking, then trim to k."""
        return max(k, self._rerank_pool) if self._rerank_enabled else k

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
            top_k=self._fetch_k(k),
            score_threshold=threshold,
            filter_payload=filter_payload or None,
        )
        retrieval_ms = (time.monotonic() - t1) * 1000

        items = self._results_to_items(results)
        deduped = self._rank_and_dedup(query, items, k)

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
                top_k=self._fetch_k(k),
                score_threshold=threshold,
                filter_payload=filter_payload,
            )
            total_retrieval_ms += (time.monotonic() - t1) * 1000

            items = self._results_to_items(results)
            deduped = self._rank_and_dedup(query, items, k)

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

    def _rank_and_dedup(
        self,
        query: str,
        items: list[SearchResultItem],
        k: int,
        max_per_doc: int = _MAX_PER_DOCUMENT,
    ) -> list[SearchResultItem]:
        """Order candidates, cap per-document, trim to k.

        When re-ranking is on, order by a hybrid score that blends the dense
        cosine similarity with lexical overlap against each chunk's heading
        path + content — so within a chapter-scoped candidate pool, the chunk
        about the exact concept asked outranks generic chapter chunks. The
        item's ``.score`` stays the raw cosine (used for the threshold gate
        and shown to the client); only the ordering changes.
        """
        if self._rerank_enabled:
            q_tokens = self._tokenize(query)
            ordered = sorted(
                items,
                key=lambda it: it.score + self._lexical_weight * self._lexical_overlap(q_tokens, it),
                reverse=True,
            )
        else:
            ordered = sorted(items, key=lambda x: x.score, reverse=True)

        doc_counts: dict[str, int] = {}
        deduped: list[SearchResultItem] = []
        for item in ordered:
            count = doc_counts.get(item.document_id, 0)
            if count < max_per_doc:
                deduped.append(item)
                doc_counts[item.document_id] = count + 1
            if len(deduped) >= k:
                break
        return deduped

    @staticmethod
    def _tokenize(text: str) -> set[str]:
        return {t for t in _TOKEN_RE.findall(text.lower()) if len(t) > 2 and t not in _STOPWORDS}

    def _lexical_overlap(self, q_tokens: set[str], item: SearchResultItem) -> float:
        """Fraction of the query's content words present in the chunk's
        heading path + content head. 0.0 when the query has no content words."""
        if not q_tokens:
            return 0.0
        heading = str(item.metadata.get("heading_path") or "")
        doc_tokens = self._tokenize(f"{heading} {item.content[:400]}")
        if not doc_tokens:
            return 0.0
        return len(q_tokens & doc_tokens) / len(q_tokens)
