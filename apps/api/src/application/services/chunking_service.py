"""Document chunking.

Two families of strategy:

- ``fixed`` / ``sliding`` — the original token-window splitter (sync). Cheap,
  deterministic, but cuts mid-sentence and counts in tiktoken, which does not
  match the embedder's own tokenizer.

- ``adaptive`` / ``semantic`` — structure-aware, dynamically-sized chunks
  (async). Text is split into structural *atoms* (headings, paragraphs,
  worked examples), then packed to a token budget that is *guarded against the
  embedder's real max* so nothing is silently truncated at embed time. When an
  embedder is available, ``semantic`` mode additionally cuts on topic shifts
  (consecutive-atom cosine drop), so chunk length follows content coherence
  rather than a constant.

The token budget is expressed in tiktoken space but bounded by
``embedder_max_tokens / safety_ratio`` so that, even though the embedder uses a
different (WordPiece) tokenizer, a packed chunk stays under its hard limit.
"""
import re
from dataclasses import dataclass, field
from typing import Literal

import tiktoken

from src.infrastructure.embeddings.base import AbstractEmbeddingProvider
from src.infrastructure.parsing.base import ParsedDocument

_PARAGRAPH_RE = re.compile(r"\n\s*\n")
_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9])")
_HEADING_KEYWORDS = re.compile(
    r"^(chapter|section|unit|lesson|topic|example|exercise|activity|question|q\.?\d*|solution|summary)\b",
    re.IGNORECASE,
)
_ATOMIC_KEYWORDS = re.compile(
    r"^(example|exercise|activity|question|q\.?\d*|solution|problem)\b",
    re.IGNORECASE,
)


@dataclass
class TextChunk:
    content: str
    chunk_index: int
    page_number: int | None = None
    char_start: int = 0
    char_end: int = 0
    token_count: int = 0
    metadata: dict = field(default_factory=dict)


@dataclass
class _Atom:
    """A structural unit of a page — one paragraph, heading, or example."""
    text: str
    token_count: int
    heading_path: str | None
    is_atomic: bool
    char_start: int


class ChunkingService:
    """Converts a ParsedDocument into a list of TextChunks."""

    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 64,
        strategy: Literal["fixed", "semantic", "sliding", "adaptive"] = "fixed",
        embedder: AbstractEmbeddingProvider | None = None,
        target_tokens: int = 350,
        min_tokens: int = 128,
        safety_ratio: float = 1.15,
        semantic_threshold: float = 0.82,
        semantic_enabled: bool = True,
    ) -> None:
        self._chunk_size = chunk_size
        self._overlap = chunk_overlap
        self._strategy = strategy
        self._embedder = embedder
        self._enc = tiktoken.get_encoding("cl100k_base")

        # Budget in tiktoken space, guarded so the chunk stays under the
        # embedder's real (WordPiece) limit even when that tokenizer is denser.
        embedder_max = embedder.max_tokens if embedder else 512
        self._effective_max = max(min_tokens, int(embedder_max / safety_ratio))
        self._target = min(target_tokens, self._effective_max)
        self._min = min(min_tokens, self._target)
        self._semantic_threshold = semantic_threshold
        self._semantic_enabled = semantic_enabled

    @property
    def strategy(self) -> str:
        return self._strategy

    @property
    def is_adaptive(self) -> bool:
        return self._strategy in ("adaptive", "semantic")

    # ── Sync entry (fixed / sliding) ─────────────────────────────────────────
    def chunk_document(
        self, document: ParsedDocument, doc_metadata: dict | None = None
    ) -> list[TextChunk]:
        chunks: list[TextChunk] = []
        idx = 0
        for page in document.pages:
            if not page.content.strip():
                continue
            page_chunks = self._chunk_text(
                text=page.content,
                page_number=page.page_number,
                base_index=idx,
                doc_metadata=doc_metadata or {},
            )
            chunks.extend(page_chunks)
            idx += len(page_chunks)
        return chunks

    # ── Async entry (adaptive / semantic) ────────────────────────────────────
    async def chunk_document_adaptive(
        self, document: ParsedDocument, doc_metadata: dict | None = None
    ) -> list[TextChunk]:
        chunks: list[TextChunk] = []
        idx = 0
        for page in document.pages:
            if not page.content.strip():
                continue
            atoms = self._structural_atoms(page.content)
            if not atoms:
                continue
            groups = await self._group_atoms(atoms)
            for group in groups:
                chunk = self._group_to_chunk(group, page.page_number, idx, doc_metadata or {})
                if chunk.content:
                    chunks.append(chunk)
                    idx += 1
        return chunks

    def count_tokens(self, text: str) -> int:
        return len(self._enc.encode(text))

    # ── Structural splitting ─────────────────────────────────────────────────
    def _structural_atoms(self, text: str) -> list[_Atom]:
        atoms: list[_Atom] = []
        current_heading: str | None = None
        cursor = 0

        for para in _PARAGRAPH_RE.split(text):
            stripped = para.strip()
            if not stripped:
                cursor += len(para) + 2
                continue

            char_start = text.find(stripped, cursor)
            if char_start < 0:
                char_start = cursor
            cursor = char_start + len(stripped)

            if self._is_heading(stripped):
                current_heading = stripped

            is_atomic = bool(_ATOMIC_KEYWORDS.match(stripped))
            tok = len(self._enc.encode(stripped))

            if tok <= self._effective_max:
                atoms.append(_Atom(stripped, tok, current_heading, is_atomic, char_start))
            else:
                # Oversized paragraph — break into sentence-packed sub-atoms.
                for sub, sub_tok, sub_start in self._split_oversized(stripped, char_start):
                    atoms.append(_Atom(sub, sub_tok, current_heading, is_atomic, sub_start))
        return atoms

    def _split_oversized(self, text: str, base_start: int) -> list[tuple[str, int, int]]:
        sentences = _SENTENCE_RE.split(text)
        out: list[tuple[str, int, int]] = []
        buf: list[str] = []
        buf_tok = 0
        search = 0
        for sent in sentences:
            s = sent.strip()
            if not s:
                continue
            stok = len(self._enc.encode(s))
            if stok > self._effective_max:
                # A single monster sentence — hard token-split as last resort.
                if buf:
                    out.append(self._flush_sentences(buf, text, base_start, search))
                    search += len(" ".join(buf))
                    buf, buf_tok = [], 0
                for piece, ptok in self._hard_token_split(s):
                    out.append((piece, ptok, base_start + text.find(piece, search)))
                continue
            if buf_tok + stok > self._effective_max and buf:
                out.append(self._flush_sentences(buf, text, base_start, search))
                search += len(" ".join(buf))
                buf, buf_tok = [], 0
            buf.append(s)
            buf_tok += stok
        if buf:
            out.append(self._flush_sentences(buf, text, base_start, search))
        return out

    def _flush_sentences(
        self, buf: list[str], text: str, base_start: int, search: int
    ) -> tuple[str, int, int]:
        joined = " ".join(buf)
        rel = text.find(buf[0], search)
        return joined, len(self._enc.encode(joined)), base_start + (rel if rel >= 0 else 0)

    def _hard_token_split(self, text: str) -> list[tuple[str, int]]:
        tokens = self._enc.encode(text)
        out: list[tuple[str, int]] = []
        for i in range(0, len(tokens), self._effective_max):
            piece = tokens[i : i + self._effective_max]
            out.append((self._enc.decode(piece).strip(), len(piece)))
        return out

    @staticmethod
    def _is_heading(paragraph: str) -> bool:
        if "\n" in paragraph or len(paragraph) > 80:
            return False
        if _HEADING_KEYWORDS.match(paragraph):
            return True
        # Short, un-punctuated, few-word line reads as a title.
        return not paragraph.endswith((".", "?", "!")) and len(paragraph.split()) <= 10

    # ── Grouping (dynamic sizing) ────────────────────────────────────────────
    async def _group_atoms(self, atoms: list[_Atom]) -> list[list[_Atom]]:
        if self._strategy == "semantic" and self._semantic_enabled and self._embedder:
            sims = await self._adjacent_similarities(atoms)
        else:
            sims = None
        return self._pack(atoms, sims)

    async def _adjacent_similarities(self, atoms: list[_Atom]) -> list[float]:
        """Cosine between each atom and its predecessor (sims[0] unused)."""
        if self._embedder is None:
            return [1.0] * len(atoms)
        result = await self._embedder.embed([a.text for a in atoms])
        vecs = result.vectors
        sims = [1.0]
        for i in range(1, len(atoms)):
            sims.append(_cosine(vecs[i - 1], vecs[i]))
        return sims

    def _pack(self, atoms: list[_Atom], sims: list[float] | None) -> list[list[_Atom]]:
        groups: list[list[_Atom]] = []
        cur: list[_Atom] = []
        cur_tokens = 0

        for i, atom in enumerate(atoms):
            if cur:
                over_budget = cur_tokens + atom.token_count > self._effective_max
                have_min = cur_tokens >= self._min
                heading_break = atom.heading_path != cur[-1].heading_path and have_min
                atomic_break = atom.is_atomic and have_min
                topic_shift = (
                    sims is not None and sims[i] < self._semantic_threshold and have_min
                )
                if over_budget or heading_break or atomic_break or topic_shift:
                    groups.append(cur)
                    cur, cur_tokens = [], 0
            cur.append(atom)
            cur_tokens += atom.token_count

        if cur:
            groups.append(cur)
        return groups

    def _group_to_chunk(
        self, group: list[_Atom], page_number: int, chunk_index: int, doc_metadata: dict
    ) -> TextChunk:
        content = "\n\n".join(a.text for a in group).strip()
        heading_path = next((a.heading_path for a in group if a.heading_path), None)
        char_start = group[0].char_start
        metadata = {**doc_metadata}
        if heading_path:
            metadata["heading_path"] = heading_path
        return TextChunk(
            content=content,
            chunk_index=chunk_index,
            page_number=page_number,
            char_start=char_start,
            char_end=char_start + len(content),
            token_count=len(self._enc.encode(content)),
            metadata=metadata,
        )

    # ── Legacy fixed / sliding ───────────────────────────────────────────────
    def _chunk_text(
        self, text: str, page_number: int, base_index: int, doc_metadata: dict
    ) -> list[TextChunk]:
        if self._strategy == "sliding":
            return self._fixed_chunks(text, page_number, base_index, doc_metadata)
        # "fixed" (and any sync fallthrough) use the token-window splitter.
        return self._fixed_chunks(text, page_number, base_index, doc_metadata)

    def _fixed_chunks(
        self, text: str, page_number: int, base_index: int, doc_metadata: dict
    ) -> list[TextChunk]:
        tokens = self._enc.encode(text)
        chunks: list[TextChunk] = []
        start = 0
        chunk_idx = base_index

        while start < len(tokens):
            end = min(start + self._chunk_size, len(tokens))
            chunk_tokens = tokens[start:end]
            content = self._enc.decode(chunk_tokens)

            char_start = len(self._enc.decode(tokens[:start]))
            char_end = char_start + len(content)

            chunks.append(
                TextChunk(
                    content=content.strip(),
                    chunk_index=chunk_idx,
                    page_number=page_number,
                    char_start=char_start,
                    char_end=char_end,
                    token_count=len(chunk_tokens),
                    metadata={**doc_metadata},
                )
            )
            chunk_idx += 1
            start += self._chunk_size - self._overlap

        return [c for c in chunks if c.content]


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)
