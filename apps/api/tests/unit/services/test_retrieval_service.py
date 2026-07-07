from unittest.mock import AsyncMock

import pytest

from src.application.services.retrieval_service import RetrievalService
from src.infrastructure.vector.base import SearchResult


@pytest.fixture
def mock_vector_store():
    store = AsyncMock()
    store.search = AsyncMock(return_value=[
        SearchResult(
            id="vec-1",
            score=0.85,
            payload={
                "document_id": "doc-1",
                "document_title": "Algorithms Chapter 1",
                "content": "Binary search is a divide and conquer algorithm.",
                "knowledge_base_id": "kb-1",
                "page_number": 3,
            },
        ),
        SearchResult(
            id="vec-2",
            score=0.72,
            payload={
                "document_id": "doc-2",
                "document_title": "Data Structures",
                "content": "A balanced BST has O(log n) search time.",
                "knowledge_base_id": "kb-1",
                "page_number": 7,
            },
        ),
    ])
    return store


@pytest.fixture
def mock_embedder():
    embedder = AsyncMock()
    embedder.embed_query = AsyncMock(return_value=[0.1] * 384)
    return embedder


@pytest.fixture
def svc(mock_vector_store, mock_embedder):
    return RetrievalService(
        vector_store=mock_vector_store,
        embedding_provider=mock_embedder,
        top_k=5,
        score_threshold=0.35,
    )


@pytest.mark.asyncio
async def test_retrieve_returns_context_with_results(svc, mock_vector_store):
    ctx, timing = await svc.retrieve("What is binary search?")
    assert ctx.has_context is True
    assert len(ctx.chunks) == 2
    assert ctx.query == "What is binary search?"
    assert "embedding_ms" in timing
    assert "retrieval_ms" in timing


@pytest.mark.asyncio
async def test_retrieve_empty_when_no_results(svc, mock_vector_store):
    mock_vector_store.search.return_value = []
    ctx, _ = await svc.retrieve("random unrelated question")
    assert ctx.has_context is False
    assert ctx.chunks == []


@pytest.mark.asyncio
async def test_retrieve_passes_kb_filter(svc, mock_vector_store):
    await svc.retrieve("search with filter", knowledge_base_id="kb-xyz")
    call_kwargs = mock_vector_store.search.call_args
    assert call_kwargs.kwargs.get("filter_payload") == {"knowledge_base_id": "kb-xyz"}


@pytest.mark.asyncio
async def test_retrieve_chunks_sorted_by_score(svc):
    ctx, _ = await svc.retrieve("sort test")
    scores = [c.score for c in ctx.chunks]
    assert scores == sorted(scores, reverse=True)


@pytest.mark.asyncio
async def test_formatted_context_contains_source_prefix(svc):
    ctx, _ = await svc.retrieve("format test")
    assert "[Source 1:" in ctx.formatted_context
    assert "Binary search" in ctx.formatted_context


# ── Hybrid re-rank (Pillar 2: within-chapter concept precision) ──────────────

def _concept_store():
    """Higher-cosine generic chunk vs. lower-cosine chunk whose heading matches
    the asked concept."""
    store = AsyncMock()
    store.search = AsyncMock(return_value=[
        SearchResult(
            id="generic",
            score=0.80,
            payload={
                "document_id": "doc-generic",
                "content": "Living organisms are made of cells and tissues in the body.",
                "knowledge_base_id": "kb-bio",
                "heading_path": "Introduction to Biology",
            },
        ),
        SearchResult(
            id="heart",
            score=0.70,
            payload={
                "document_id": "doc-heart",
                "content": "The heart pumps blood through four chambers to the body.",
                "knowledge_base_id": "kb-bio",
                "heading_path": "The Human Heart",
            },
        ),
    ])
    return store


@pytest.mark.asyncio
async def test_rerank_promotes_concept_match(mock_embedder):
    svc = RetrievalService(
        vector_store=_concept_store(), embedding_provider=mock_embedder,
        top_k=5, rerank_enabled=True, lexical_weight=0.25,
    )
    ctx, _ = await svc.retrieve("explain the heart chambers")
    # Lower cosine (0.70) but heading + content match the concept → ranks first.
    assert ctx.chunks[0].content.startswith("The heart pumps")
    # Raw cosine is preserved for the client / threshold gate.
    assert ctx.chunks[0].score == 0.70


@pytest.mark.asyncio
async def test_rerank_disabled_keeps_pure_cosine_order(mock_embedder):
    svc = RetrievalService(
        vector_store=_concept_store(), embedding_provider=mock_embedder,
        top_k=5, rerank_enabled=False,
    )
    ctx, _ = await svc.retrieve("explain the heart chambers")
    # Without re-rank, the higher-cosine generic chunk stays on top.
    assert ctx.chunks[0].score == 0.80


@pytest.mark.asyncio
async def test_rerank_fetches_wider_pool(mock_embedder):
    store = _concept_store()
    svc = RetrievalService(
        vector_store=store, embedding_provider=mock_embedder,
        top_k=5, rerank_enabled=True, rerank_pool=20,
    )
    await svc.retrieve("heart")
    # The store is asked for the wider pool, not just top_k.
    assert store.search.call_args.kwargs["top_k"] == 20


def test_lexical_overlap_ignores_stopwords():
    q = RetrievalService._tokenize("what is the heart and how does it work")
    assert "heart" in q
    assert "work" in q
    assert "the" not in q and "is" not in q and "how" not in q
