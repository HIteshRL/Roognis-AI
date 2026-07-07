from types import SimpleNamespace

import pytest

from src.application.services.chunking_service import ChunkingService
from src.application.services.vector_service import VectorService
from src.infrastructure.embeddings.base import EmbeddingResult
from src.infrastructure.parsing.base import ParsedDocument, ParsedPage


@pytest.fixture
def svc():
    return ChunkingService(chunk_size=100, chunk_overlap=20, strategy="fixed")


def _doc(text: str, page: int = 1) -> ParsedDocument:
    return ParsedDocument(pages=[ParsedPage(page_number=page, content=text)])


class _FakeEmbedder:
    """Returns a fixed vector per text based on a cluster keyword — lets us
    drive semantic boundaries deterministically without a real model."""

    def __init__(self, max_tokens: int = 512) -> None:
        self._max = max_tokens

    @property
    def max_tokens(self) -> int:
        return self._max

    async def embed(self, texts: list[str]) -> EmbeddingResult:
        vecs = []
        for t in texts:
            if "photosynthesis" in t.lower():
                vecs.append([1.0, 0.0, 0.0])
            elif "gravity" in t.lower():
                vecs.append([0.0, 1.0, 0.0])
            else:
                vecs.append([0.0, 0.0, 1.0])
        return EmbeddingResult(vectors=vecs, model="fake", dimension=3)


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


# ── Adaptive / semantic chunking ─────────────────────────────────────────────

def _adaptive_svc(strategy="adaptive", embedder_max=40, **kw):
    return ChunkingService(
        strategy=strategy,
        embedder=_FakeEmbedder(embedder_max),
        min_tokens=kw.pop("min_tokens", 1),
        target_tokens=kw.pop("target_tokens", embedder_max),
        safety_ratio=kw.pop("safety_ratio", 1.0),
        **kw,
    )


@pytest.mark.asyncio
async def test_adaptive_respects_token_cap_invariant():
    # effective_max = 40 / 1.0 = 40 — no emitted chunk may exceed it.
    svc = _adaptive_svc(embedder_max=40)
    text = "\n\n".join(f"Sentence number {i} about many varied things." for i in range(30))
    chunks = await svc.chunk_document_adaptive(_doc(text))
    assert chunks
    for c in chunks:
        assert c.token_count <= 40


@pytest.mark.asyncio
async def test_adaptive_starts_new_chunk_on_heading():
    text = (
        "Newton's Laws\n\n"
        "An object in motion stays in motion unless acted upon by a force here.\n\n"
        "Photosynthesis\n\n"
        "Plants convert sunlight into chemical energy stored as sugar molecules."
    )
    svc = _adaptive_svc(strategy="adaptive", embedder_max=512, min_tokens=1)
    chunks = await svc.chunk_document_adaptive(_doc(text))
    joined = [c.content for c in chunks]
    # The two headings must not end up glued into one chunk.
    assert not any("Newton's Laws" in c and "Photosynthesis" in c for c in joined)


@pytest.mark.asyncio
async def test_adaptive_sets_heading_path_metadata():
    text = "Chapter 1 Forces\n\nA force is a push or a pull acting upon an object."
    svc = _adaptive_svc(strategy="adaptive", embedder_max=512, min_tokens=1)
    chunks = await svc.chunk_document_adaptive(_doc(text))
    assert any(c.metadata.get("heading_path") == "Chapter 1 Forces" for c in chunks)


@pytest.mark.asyncio
async def test_semantic_mode_splits_on_topic_shift():
    # Two coherent paragraphs per topic; the fake embedder makes the two
    # topics orthogonal, so the boundary falls between them.
    text = (
        "Photosynthesis converts light into sugar in the chloroplast.\n\n"
        "Photosynthesis also releases oxygen as a byproduct of the reaction.\n\n"
        "Gravity is the attractive force between two masses in the universe.\n\n"
        "Gravity keeps the planets in orbit around the sun continuously."
    )
    svc = _adaptive_svc(strategy="semantic", embedder_max=512, min_tokens=1,
                        semantic_threshold=0.5)
    chunks = await svc.chunk_document_adaptive(_doc(text))
    assert len(chunks) >= 2
    # No chunk should mix the two orthogonal topics.
    for c in chunks:
        assert not ("Photosynthesis" in c.content and "Gravity" in c.content)


@pytest.mark.asyncio
async def test_oversized_paragraph_is_split_under_cap():
    svc = _adaptive_svc(embedder_max=30, safety_ratio=1.0, min_tokens=1)
    big = " ".join(f"token{i}" for i in range(200))  # one huge paragraph
    chunks = await svc.chunk_document_adaptive(_doc(big))
    assert len(chunks) > 1
    for c in chunks:
        assert c.token_count <= 30


# ── Contextual embed-text (Tier 3) ───────────────────────────────────────────

def test_embed_text_prepends_curriculum_context():
    chunk = SimpleNamespace(content="It equals mass times acceleration.",
                            metadata={"heading_path": "Newton's Second Law"})
    text = VectorService._embed_text(chunk, "Physics Textbook",
                                     {"subject": "Physics", "chapter": "Forces"})
    assert text.startswith("Physics > Forces > Newton's Second Law:")
    assert "It equals mass times acceleration." in text


def test_embed_text_no_context_returns_plain_content():
    chunk = SimpleNamespace(content="Bare content.", metadata={})
    assert VectorService._embed_text(chunk, None, None) == "Bare content."
