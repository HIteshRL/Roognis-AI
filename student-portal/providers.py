"""
Pluggable adapters that let the REAL rag-standalone AgenticRagService run with
zero infrastructure (no Qdrant / embeddings), and flip to real Groq when a key
is set. Each class implements a rag-standalone interface:

  InMemoryRetrieval   -> same shape as RetrievalService (returns RetrievedContext)
  CorpusGuardrail     -> subclass of GuardrailService (real safety rules +
                         deterministic, corpus-based subject adherence)
  OfflineTutorProvider-> AbstractLLMProvider (extractive answers, used when there
                         is no GROQ_API_KEY)
"""
import re
import sys
from collections.abc import AsyncGenerator
from pathlib import Path

# rag-standalone provides the `src.*` package we build on.
_RAG = Path(__file__).resolve().parent.parent / "rag-standalone"
if str(_RAG) not in sys.path:
    sys.path.insert(0, str(_RAG))

from src.application.dtos.agentic import RelevanceVerdict  # noqa: E402
from src.application.dtos.knowledge import RetrievedContext, SearchResultItem  # noqa: E402
from src.application.services.guardrail_service import GuardrailService  # noqa: E402
from src.infrastructure.llm.base import (  # noqa: E402
    AbstractLLMProvider,
    LLMConfig,
    LLMMessage,
    LLMResponse,
)

_STOP = {
    "the", "a", "an", "of", "to", "in", "and", "or", "is", "are", "was", "were",
    "what", "why", "how", "who", "when", "where", "which", "explain", "define",
    "tell", "give", "describe", "difference", "between", "about", "this", "that",
    "it", "its", "for", "on", "with", "as", "by", "at", "from", "into", "do",
    "does", "did", "can", "could", "you", "your", "me", "my", "i", "we", "they",
    "he", "she", "please", "some", "any", "all", "will", "would", "should",
    "there", "their", "them", "than", "then", "also", "have", "has", "had", "be",
}


def tokens(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", (text or "").lower())
            if len(w) >= 3 and w not in _STOP}


def _overlap(q: set[str], target: set[str]) -> float:
    if not q:
        return 0.0
    return len(q & target) / len(q)


def sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text or "") if s.strip()]


class InMemoryRetrieval:
    """Keyword-overlap retrieval over a chapter's sentences. Same interface as
    the real RetrievalService (retrieve -> (RetrievedContext, timing))."""

    def __init__(self, chapters: dict[str, dict], top_k: int = 4) -> None:
        # chapters: chapter_id -> {"title": str, "chunks": [str, ...]}
        self._chapters = chapters
        self._top_k = top_k

    async def retrieve(self, query: str, knowledge_base_id: str | None = None):
        q = tokens(query)
        ch = self._chapters.get(knowledge_base_id or "", {})
        title, chunks = ch.get("title"), ch.get("chunks", [])
        scored = sorted(
            ((_overlap(q, tokens(c)), i, c) for i, c in enumerate(chunks)),
            key=lambda t: -t[0],
        )[: self._top_k]
        items = [
            SearchResultItem(
                chunk_id=f"{knowledge_base_id}:{i}", document_id=knowledge_base_id or "",
                document_title=title, content=c, score=round(float(score), 3),
                page_number=None, metadata={},
            )
            for score, i, c in scored if score > 0
        ]
        ctx = RetrievedContext(chunks=items, has_context=bool(items), query=query)
        return ctx, {"embedding_ms": 0.0, "retrieval_ms": 0.0}


class DbRetrieval:
    """Keyword-overlap retrieval over a chapter's chunks stored in SQLite
    (seed content + uploaded-PDF chunks). Same interface as RetrievalService."""

    def __init__(self, top_k: int = 4) -> None:
        self._top_k = top_k

    async def retrieve(self, query: str, knowledge_base_id: str | None = None):
        import store
        chid = knowledge_base_id or ""
        q = tokens(query)
        chapter = store.get_chapter(chid)
        title = None
        if chapter:
            room = store.get_classroom(chapter["classroom_id"])
            title = f'{room["name"]} — {chapter["title"]}' if room else chapter["title"]
        chunks = store.get_chapter_chunks(chid)
        scored = sorted(
            ((_overlap(q, tokens(c)), i, c) for i, c in enumerate(chunks)),
            key=lambda t: -t[0],
        )[: self._top_k]
        items = [
            SearchResultItem(
                chunk_id=f"{chid}:{i}", document_id=chid, document_title=title,
                content=c, score=round(float(s), 3), page_number=None, metadata={},
            )
            for s, i, c in scored if s > 0
        ]
        ctx = RetrievedContext(chunks=items, has_context=bool(items), query=query)
        return ctx, {"embedding_ms": 0.0, "retrieval_ms": 0.0}


class CorpusGuardrail(GuardrailService):
    """Real deterministic safety rules (inherited) + a corpus-based subject gate
    that works with or without an LLM — a question is off-topic if it barely
    overlaps the whole subject's vocabulary."""

    def __init__(self, subject_corpus: dict[str, set[str]], subject_floor: float = 0.34) -> None:
        super().__init__(llm=None)
        self._corpus = subject_corpus
        self._floor = subject_floor

    async def check_subject_relevance(
        self, question: str, subject: str | None, chapter: str | None = None
    ) -> RelevanceVerdict:
        if not subject:
            return RelevanceVerdict(True, 1.0, "no subject")
        q = tokens(question)
        if not q:
            return RelevanceVerdict(True, 0.0, "no content words")
        score = _overlap(q, self._corpus.get(subject, set()))
        return RelevanceVerdict(score >= self._floor, round(score, 3),
                                f"subject overlap {score:.2f}")


class OfflineTutorProvider(AbstractLLMProvider):
    """Extractive, grounded answers built from the retrieved chapter context —
    used when no GROQ_API_KEY is present so the demo runs fully offline."""

    @property
    def provider_name(self) -> str:
        return "offline-tutor"

    async def complete(self, messages: list[LLMMessage], config: LLMConfig) -> LLMResponse:
        system = next((m.content for m in messages if m.role == "system"), "")
        question = next((m.content for m in reversed(messages) if m.role == "user"), "")

        m = re.search(r"CURRICULUM CONTEXT ---(.*?)--- END CONTEXT", system, re.S)
        context = m.group(1) if m else system
        context = re.sub(r"\[Source \d+:[^\]]*\]", " ", context)  # drop source headers

        q = tokens(question)
        ranked = sorted(sentences(context), key=lambda s: -_overlap(q, tokens(s)))
        picked = [s for s in ranked[:2] if _overlap(q, tokens(s)) > 0] or ranked[:1]
        body = " ".join(picked).strip()
        answer = (
            f"Here's what your chapter material explains: {body}"
            if body else "I couldn't find that in this chapter's material."
        )
        return LLMResponse(content=answer, model="offline-tutor", usage=None)

    async def stream(
        self, messages: list[LLMMessage], config: LLMConfig
    ) -> AsyncGenerator[str, None]:
        resp = await self.complete(messages, config)
        yield resp.content

    async def health_check(self) -> bool:
        return True
