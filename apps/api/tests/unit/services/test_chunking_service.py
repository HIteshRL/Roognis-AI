import pytest
from src.application.services.chunking_service import ChunkingService
from src.infrastructure.parsing.base import ParsedDocument, ParsedPage


@pytest.fixture
def svc():
    return ChunkingService(chunk_size=100, chunk_overlap=20, strategy="fixed")


def _doc(text: str, page: int = 1) -> ParsedDocument:
    return ParsedDocument(pages=[ParsedPage(page_number=page, content=text)])


def test_empty_document_returns_no_chunks(svc):
    assert svc.chunk_document(_doc("")) == []


def test_short_text_produces_single_chunk(svc):
    chunks = svc.chunk_document(_doc("hello world"))
    assert len(chunks) == 1
    assert "hello" in chunks[0].content


def test_chunk_index_is_sequential(svc):
    long_text = "word " * 300
    chunks = svc.chunk_document(_doc(long_text))
    for i, c in enumerate(chunks):
        assert c.chunk_index == i


def test_page_number_propagated(svc):
    doc = ParsedDocument(pages=[
        ParsedPage(page_number=1, content="page one content"),
        ParsedPage(page_number=2, content="page two content"),
    ])
    chunks = svc.chunk_document(doc)
    assert chunks[0].page_number == 1
    assert chunks[-1].page_number == 2


def test_token_count_positive(svc):
    chunks = svc.chunk_document(_doc("some text to chunk"))
    for c in chunks:
        assert c.token_count > 0


def test_overlap_produces_more_chunks_than_no_overlap():
    svc_overlap = ChunkingService(chunk_size=50, chunk_overlap=25)
    svc_no_overlap = ChunkingService(chunk_size=50, chunk_overlap=0)
    text = "word " * 100
    doc = _doc(text)
    assert len(svc_overlap.chunk_document(doc)) >= len(svc_no_overlap.chunk_document(doc))


def test_multipage_chunks_have_correct_indices():
    svc = ChunkingService(chunk_size=20, chunk_overlap=0)
    doc = ParsedDocument(pages=[
        ParsedPage(page_number=p, content="content " * 10) for p in range(1, 4)
    ])
    chunks = svc.chunk_document(doc)
    indices = [c.chunk_index for c in chunks]
    assert indices == sorted(set(indices))
