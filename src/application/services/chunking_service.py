from dataclasses import dataclass, field
from typing import Literal

import tiktoken

from src.infrastructure.parsing.base import ParsedDocument


@dataclass
class TextChunk:
    content: str
    chunk_index: int
    page_number: int | None = None
    char_start: int = 0
    char_end: int = 0
    token_count: int = 0
    metadata: dict = field(default_factory=dict)


class ChunkingService:
    """
    Converts a ParsedDocument into a list of TextChunks.
    Strategy, size, and overlap are configurable.
    Token counting uses tiktoken cl100k_base (matches most modern LLMs).
    """

    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 64,
        strategy: Literal["fixed", "semantic", "sliding"] = "fixed",
    ) -> None:
        self._chunk_size = chunk_size
        self._overlap = chunk_overlap
        self._strategy = strategy
        self._enc = tiktoken.get_encoding("cl100k_base")

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

    def _chunk_text(
        self,
        text: str,
        page_number: int,
        base_index: int,
        doc_metadata: dict,
    ) -> list[TextChunk]:
        if self._strategy == "fixed":
            return self._fixed_chunks(text, page_number, base_index, doc_metadata)
        if self._strategy == "sliding":
            return self._sliding_chunks(text, page_number, base_index, doc_metadata)
        # "semantic" falls back to fixed for Phase 0.2 (requires NLP model in 0.3+)
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

    def _sliding_chunks(
        self, text: str, page_number: int, base_index: int, doc_metadata: dict
    ) -> list[TextChunk]:
        # Sliding window with full overlap — identical to fixed with overlap already set
        return self._fixed_chunks(text, page_number, base_index, doc_metadata)

    def count_tokens(self, text: str) -> int:
        return len(self._enc.encode(text))
