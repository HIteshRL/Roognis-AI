"""
Tests for curriculum-filtered retrieval.
Verifies that the CurriculumFilter.to_payload_filter() contract is correct,
that RetrievalService passes the filter to the vector store, and that
RagService assembles timing + structured responses correctly.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.application.dtos.knowledge import (
    CurriculumFilter,
    RagQueryRequest,
    SearchResultItem,
)
from src.application.services.retrieval_service import RetrievalService
from src.application.services.rag_service import RagService
from src.application.services.context_validation_service import ContextValidationService
from src.application.services.prompt_assembly_service import PromptAssemblyService
from src.infrastructure.embeddings.base import EmbeddingResult
from src.infrastructure.vector.base import SearchResult


# ── CurriculumFilter ──────────────────────────────────────────────────────────

def test_curriculum_filter_empty_produces_empty_dict():
    f = CurriculumFilter()
    assert f.to_payload_filter() == {}


def test_curriculum_filter_all_fields():
    f = CurriculumFilter(
        institution="MIT",
        grade="7",
        subject="Science",
        chapter="Nutrition in Plants",
        topic="Photosynthesis",
    )
    payload = f.to_payload_filter()
    assert payload == {
        "institution": "MIT",
        "grade": "7",
        "subject": "Science",
        "chapter": "Nutrition in Plants",
        "topic": "Photosynthesis",
    }


def test_curriculum_filter_partial():
    f = CurriculumFilter(grade="7", subject="Science")
    payload = f.to_payload_filter()
    assert payload == {"grade": "7", "subject": "Science"}
    assert "chapter" not in payload
    assert "topic" not in payload


def test_curriculum_filter_knowledge_base_id():
    f = CurriculumFilter(knowledge_base_id="kb-123", grade="8")
    payload = f.to_payload_filter()
    assert payload["knowledge_base_id"] == "kb-123"
    assert payload["grade"] == "8"


# ── RetrievalService with curriculum filter ───────────────────────────────────

@pytest.mark.asyncio
async def test_retrieval_passes_curriculum_filter_to_vector_store():
    mock_store = AsyncMock()
    mock_store.search = AsyncMock(return_value=[
        SearchResult(
            id="chunk-1",
            score=0.88,
            payload={
                "document_id": "doc-1",
                "document_title": "Nutrition in Plants",
                "content": "Photosynthesis is the process...",
                "grade": "7",
                "subject": "Science",
                "chapter": "Nutrition in Plants",
            },
        )
    ])

    mock_embedder = AsyncMock()
    mock_embedder.embed_query = AsyncMock(return_value=[0.1] * 384)
    mock_embedder.dimension = 384

    svc = RetrievalService(
        vector_store=mock_store,
        embedding_provider=mock_embedder,
        top_k=5,
        score_threshold=0.35,
    )

    curriculum = {"grade": "7", "subject": "Science", "chapter": "Nutrition in Plants"}
    context, timing = await svc.retrieve(
        query="What is photosynthesis?",
        curriculum_filter=curriculum,
    )

    # Vector store must have been called with the curriculum filter
    call_kwargs = mock_store.search.call_args.kwargs
    assert call_kwargs["filter_payload"] == curriculum
    assert context.has_context is True
    assert len(context.chunks) == 1
    assert context.chunks[0].score == 0.88
    assert "embedding_ms" in timing
    assert "retrieval_ms" in timing


@pytest.mark.asyncio
async def test_retrieval_no_results_returns_no_context():
    mock_store = AsyncMock()
    mock_store.search = AsyncMock(return_value=[])

    mock_embedder = AsyncMock()
    mock_embedder.embed_query = AsyncMock(return_value=[0.1] * 384)

    svc = RetrievalService(
        vector_store=mock_store,
        embedding_provider=mock_embedder,
    )

    context, timing = await svc.retrieve(
        query="What is mitosis?",
        curriculum_filter={"grade": "7", "subject": "Science"},
    )

    assert context.has_context is False
    assert context.chunks == []


@pytest.mark.asyncio
async def test_retrieval_without_filter_passes_none_to_store():
    mock_store = AsyncMock()
    mock_store.search = AsyncMock(return_value=[])

    mock_embedder = AsyncMock()
    mock_embedder.embed_query = AsyncMock(return_value=[0.1] * 384)

    svc = RetrievalService(vector_store=mock_store, embedding_provider=mock_embedder)
    await svc.retrieve(query="hello")

    call_kwargs = mock_store.search.call_args.kwargs
    assert call_kwargs["filter_payload"] is None


# ── ContextValidationService ──────────────────────────────────────────────────

def test_context_validation_filters_low_scores():
    from src.application.dtos.knowledge import RetrievedContext

    low_chunk = SearchResultItem(
        chunk_id="c1",
        document_id="d1",
        document_title="X",
        content="short",
        score=0.2,
        page_number=None,
        metadata={},
    )
    high_chunk = SearchResultItem(
        chunk_id="c2",
        document_id="d2",
        document_title="Y",
        content="Photosynthesis is the process by which plants convert sunlight to food.",
        score=0.85,
        page_number=1,
        metadata={},
    )
    context = RetrievedContext(
        chunks=[low_chunk, high_chunk],
        has_context=True,
        query="photosynthesis",
    )
    svc = ContextValidationService(min_score=0.35)
    result = svc.validate(context)
    # low_chunk score 0.2 < 0.35 → filtered out; also "short" < 50 chars
    assert len(result.chunks) == 1
    assert result.chunks[0].chunk_id == "c2"


# ── RagService ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_rag_service_returns_structured_response():
    from src.application.dtos.knowledge import RetrievedContext
    from src.infrastructure.llm.base import LLMResponse, LLMUsage

    chunk = SearchResultItem(
        chunk_id="c1",
        document_id="d1",
        document_title="Nutrition in Plants",
        content="Photosynthesis is the process by which green plants make their own food.",
        score=0.90,
        page_number=5,
        metadata={"grade": "7", "subject": "Science", "chapter": "Nutrition in Plants"},
    )
    mock_context = RetrievedContext(chunks=[chunk], has_context=True, query="What is photosynthesis?")
    mock_timing = {"embedding_ms": 12.3, "retrieval_ms": 45.6}

    mock_retrieval = AsyncMock()
    mock_retrieval.retrieve = AsyncMock(return_value=(mock_context, mock_timing))

    mock_prompt_assembly = AsyncMock()
    mock_prompt_assembly.build_messages = AsyncMock(return_value=[])

    mock_validation = MagicMock()
    mock_validation.validate = MagicMock(return_value=mock_context)

    mock_llm = AsyncMock()
    mock_llm.complete = AsyncMock(return_value=LLMResponse(
        content="Photosynthesis is the process by which green plants make food.",
        model="llama-3.3-70b-versatile",
        usage=LLMUsage(prompt_tokens=100, completion_tokens=50, total_tokens=150),
    ))

    svc = RagService(
        retrieval_svc=mock_retrieval,
        prompt_assembly_svc=mock_prompt_assembly,
        context_validation_svc=mock_validation,
        llm_provider=mock_llm,
    )

    req = RagQueryRequest(
        query="What is photosynthesis?",
        curriculum=CurriculumFilter(grade="7", subject="Science"),
        top_k=5,
    )
    result = await svc.query(req)

    assert result.has_context is True
    assert "photosynthesis" in result.answer.lower()
    assert len(result.chunks) == 1
    assert result.chunks[0].grade == "7"
    assert result.chunks[0].subject == "Science"
    assert result.observability.embedding_ms == 12.3
    assert result.observability.retrieval_ms == 45.6
    assert result.observability.chunks_used == 1
    assert result.observability.token_usage["total_tokens"] == 150
    assert result.curriculum_filter == {"grade": "7", "subject": "Science"}


@pytest.mark.asyncio
async def test_rag_service_no_context_strict_reply():
    from src.application.dtos.knowledge import RetrievedContext
    from src.infrastructure.llm.base import LLMResponse, LLMUsage

    empty_context = RetrievedContext(chunks=[], has_context=False, query="What is mitosis?")
    mock_retrieval = AsyncMock()
    mock_retrieval.retrieve = AsyncMock(return_value=(empty_context, {"embedding_ms": 10.0, "retrieval_ms": 5.0}))

    mock_prompt_assembly = AsyncMock()
    mock_prompt_assembly.build_messages = AsyncMock(return_value=[])

    mock_validation = MagicMock()
    mock_validation.validate = MagicMock(return_value=empty_context)

    strict_reply = "I cannot find this information in the provided curriculum."
    mock_llm = AsyncMock()
    mock_llm.complete = AsyncMock(return_value=LLMResponse(
        content=strict_reply,
        model="llama-3.3-70b-versatile",
        usage=LLMUsage(prompt_tokens=50, completion_tokens=15, total_tokens=65),
    ))

    svc = RagService(
        retrieval_svc=mock_retrieval,
        prompt_assembly_svc=mock_prompt_assembly,
        context_validation_svc=mock_validation,
        llm_provider=mock_llm,
    )

    result = await svc.query(RagQueryRequest(
        query="What is mitosis?",
        curriculum=CurriculumFilter(grade="7", subject="Science"),
    ))

    assert result.has_context is False
    assert result.chunks == []
    assert result.answer == strict_reply


# ── Metadata propagation ──────────────────────────────────────────────────────

def test_curriculum_filter_none_values_excluded():
    f = CurriculumFilter(grade="7", subject=None, chapter=None)
    payload = f.to_payload_filter()
    assert "subject" not in payload
    assert "chapter" not in payload
    assert payload == {"grade": "7"}
