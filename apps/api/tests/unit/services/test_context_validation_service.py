import pytest
from src.application.dtos.knowledge import RetrievedContext, SearchResultItem
from src.application.services.context_validation_service import ContextValidationService


def _chunk(content: str, score: float) -> SearchResultItem:
    return SearchResultItem(
        chunk_id="c1",
        document_id="d1",
        document_title="Test Doc",
        content=content,
        score=score,
        page_number=None,
        metadata={},
    )


def _ctx(chunks: list[SearchResultItem]) -> RetrievedContext:
    return RetrievedContext(chunks=chunks, has_context=bool(chunks), query="test")


@pytest.fixture
def svc():
    return ContextValidationService(min_score=0.35)


def test_filters_low_score_chunks(svc):
    ctx = _ctx([_chunk("a" * 100, 0.2), _chunk("b" * 100, 0.9)])
    result = svc.validate(ctx)
    assert len(result.chunks) == 1
    assert result.chunks[0].score == 0.9


def test_filters_short_content(svc):
    ctx = _ctx([_chunk("hi", 0.9), _chunk("x" * 100, 0.9)])
    result = svc.validate(ctx)
    assert len(result.chunks) == 1


def test_all_valid_chunks_pass(svc):
    chunks = [_chunk("x" * 100, 0.8) for _ in range(3)]
    result = svc.validate(_ctx(chunks))
    assert len(result.chunks) == 3


def test_empty_context_stays_empty(svc):
    result = svc.validate(_ctx([]))
    assert not result.has_context
    assert result.chunks == []


def test_has_context_false_when_all_filtered(svc):
    ctx = _ctx([_chunk("x" * 100, 0.1)])
    result = svc.validate(ctx)
    assert result.has_context is False
