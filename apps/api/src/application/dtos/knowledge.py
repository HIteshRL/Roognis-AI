from pydantic import BaseModel, Field

# ── Knowledge Base ────────────────────────────────────────────────────────────

class CreateKnowledgeBaseRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    institution: str | None = None
    subject: str | None = None
    grade: str | None = None
    chapter: str | None = None
    topic: str | None = None
    language: str = "en"


class KnowledgeBaseResponse(BaseModel):
    id: str
    name: str
    description: str | None
    institution: str | None
    subject: str | None
    grade: str | None
    chapter: str | None
    topic: str | None
    language: str
    is_active: bool
    created_by: str
    document_count: int = 0
    created_at: str
    updated_at: str


# ── Document ──────────────────────────────────────────────────────────────────

class DocumentUploadResponse(BaseModel):
    id: str
    knowledge_base_id: str
    filename: str
    file_type: str
    file_size: int
    status: str
    job_id: str
    created_at: str


class DocumentResponse(BaseModel):
    id: str
    knowledge_base_id: str
    filename: str
    title: str | None
    description: str | None
    file_type: str
    file_size: int
    status: str
    chunk_count: int
    error_message: str | None
    created_at: str
    updated_at: str


# ── Chunk ─────────────────────────────────────────────────────────────────────

class ChunkResponse(BaseModel):
    id: str
    document_id: str
    chunk_index: int
    content: str
    token_count: int
    page_number: int | None
    metadata: dict


# ── Ingestion Job ─────────────────────────────────────────────────────────────

class IngestionJobResponse(BaseModel):
    id: str
    document_id: str
    status: str
    progress: int
    error_message: str | None
    created_at: str
    updated_at: str


# ── Search ────────────────────────────────────────────────────────────────────

class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    knowledge_base_id: str | None = None
    top_k: int = Field(default=5, ge=1, le=20)
    score_threshold: float = Field(default=0.35, ge=0.0, le=1.0)


class SearchResultItem(BaseModel):
    chunk_id: str
    document_id: str
    document_title: str | None
    content: str
    score: float
    page_number: int | None
    metadata: dict


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResultItem]
    total_found: int
    knowledge_base_id: str | None


# ── RAG context (internal DTO, not exposed to API) ────────────────────────────

class RetrievedContext(BaseModel):
    chunks: list[SearchResultItem]
    has_context: bool
    query: str

    @property
    def formatted_context(self) -> str:
        if not self.chunks:
            return ""
        parts = []
        for i, chunk in enumerate(self.chunks, start=1):
            source = chunk.document_title or chunk.document_id
            page = f", page {chunk.page_number}" if chunk.page_number else ""
            scope = ""
            subject = chunk.metadata.get("subject", "")
            chapter = chunk.metadata.get("chapter", "")
            if subject:
                scope = f" | {subject}"
                if chapter:
                    scope += f" > {chapter}"
            parts.append(
                f"[Source {i}: {source}{page}{scope}]\n{chunk.content}"
            )
        return "\n\n---\n\n".join(parts)

    @property
    def citation_list(self) -> str:
        seen: set[str] = set()
        lines: list[str] = []
        for chunk in self.chunks:
            doc_id = chunk.document_id
            if doc_id not in seen:
                seen.add(doc_id)
                title = chunk.document_title or f"Document {doc_id[:8]}"
                lines.append(f"- {title}")
        return "\n".join(lines)


# ── RAG Query (curriculum-bound) ──────────────────────────────────────────────

class CurriculumFilter(BaseModel):
    """Strict academic hierarchy filter — all provided fields must match."""
    knowledge_base_id: str | None = None
    institution: str | None = None
    grade: str | None = None
    subject: str | None = None
    chapter: str | None = None
    topic: str | None = None

    def to_payload_filter(self) -> dict[str, str]:
        """Returns only non-None fields as Qdrant payload filter dict."""
        result: dict[str, str] = {}
        if self.knowledge_base_id:
            result["knowledge_base_id"] = self.knowledge_base_id
        if self.institution:
            result["institution"] = self.institution
        if self.grade:
            result["grade"] = self.grade
        if self.subject:
            result["subject"] = self.subject
        if self.chapter:
            result["chapter"] = self.chapter
        if self.topic:
            result["topic"] = self.topic
        return result


class RagUploadRequest(BaseModel):
    """Metadata carried alongside a document upload."""
    knowledge_base_id: str
    title: str | None = None
    description: str | None = None
    # Academic override — if omitted, inherited from the knowledge base
    grade: str | None = None
    chapter: str | None = None
    topic: str | None = None


class RagQueryRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    curriculum: CurriculumFilter = Field(default_factory=CurriculumFilter)
    top_k: int = Field(default=5, ge=1, le=20)
    score_threshold: float = Field(default=0.35, ge=0.0, le=1.0)
    include_chunks: bool = True


class RagChunkResult(BaseModel):
    chunk_id: str
    document_id: str
    document_title: str | None
    content: str
    score: float
    page_number: int | None
    grade: str | None
    subject: str | None
    chapter: str | None
    topic: str | None


class RagObservability(BaseModel):
    embedding_ms: float
    retrieval_ms: float
    llm_ms: float
    total_ms: float
    chunks_retrieved: int
    chunks_used: int
    similarity_scores: list[float]
    token_usage: dict[str, int]
    cache_hit: bool = False


class RagQueryResponse(BaseModel):
    query: str
    answer: str
    has_context: bool
    chunks: list[RagChunkResult]
    curriculum_filter: dict[str, str]
    observability: RagObservability
