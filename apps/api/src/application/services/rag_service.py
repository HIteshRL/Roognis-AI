"""
RagService — curriculum-bound RAG orchestrator.

Enforces strict academic filtering: every query must stay within the
declared institution / grade / subject / chapter scope.  The LLM receives
only context retrieved from within those bounds and is instructed to reply
"I cannot find this information in the provided curriculum." when nothing is found.
"""
import time

import structlog

from src.application.dtos.knowledge import (
    RagChunkResult,
    RagObservability,
    RagQueryRequest,
    RagQueryResponse,
)
from src.application.services.context_validation_service import ContextValidationService
from src.application.services.prompt_assembly_service import PromptAssemblyService
from src.application.services.response_cache_service import ResponseCacheService
from src.application.services.retrieval_service import RetrievalService
from src.infrastructure.llm.base import AbstractLLMProvider, LLMConfig

logger = structlog.get_logger(__name__)

_DEFAULT_MODEL = "llama-3.3-70b-versatile"


class RagService:
    """
    Single entry point for curriculum-filtered RAG queries.
    Returns a structured response with answer, retrieved chunks, and timing.
    """

    def __init__(
        self,
        retrieval_svc: RetrievalService,
        prompt_assembly_svc: PromptAssemblyService,
        context_validation_svc: ContextValidationService,
        llm_provider: AbstractLLMProvider,
        llm_model: str = _DEFAULT_MODEL,
        response_cache_svc: ResponseCacheService | None = None,
    ) -> None:
        self._retrieval = retrieval_svc
        self._prompt_assembly = prompt_assembly_svc
        self._context_validation = context_validation_svc
        self._llm = llm_provider
        self._llm_model = llm_model
        self._cache = response_cache_svc

    async def query(self, request: RagQueryRequest) -> RagQueryResponse:
        t_total = time.monotonic()

        curriculum_payload = request.curriculum.to_payload_filter()

        # ── Semantic cache check ────────────────────────────────────────────────
        cache_scope = {**curriculum_payload, "_include_chunks": request.include_chunks}
        if self._cache:
            cached = await self._cache.get(request.query, cache_scope)
            if cached:
                logger.info("rag_cache_hit", query_len=len(request.query))
                cached["observability"]["cache_hit"] = True
                return RagQueryResponse(**cached)

        # ── Retrieve ──────────────────────────────────────────────────────────
        raw_context, retrieve_timing = await self._retrieval.retrieve(
            query=request.query,
            curriculum_filter=curriculum_payload or None,
            top_k=request.top_k,
            score_threshold=request.score_threshold,
        )

        validated = self._context_validation.validate(raw_context)

        # ── Build grounded prompt ─────────────────────────────────────────────
        llm_messages = await self._prompt_assembly.build_messages(
            user_message=request.query,
            history=[],
            context=validated,
        )

        # ── LLM call ─────────────────────────────────────────────────────────
        t_llm = time.monotonic()
        config = LLMConfig(model=self._llm_model, temperature=0.2, stream=False)
        llm_response = await self._llm.complete(llm_messages, config)
        llm_ms = (time.monotonic() - t_llm) * 1000

        total_ms = (time.monotonic() - t_total) * 1000

        # ── Build response ────────────────────────────────────────────────────
        chunk_results = [
            RagChunkResult(
                chunk_id=c.chunk_id,
                document_id=c.document_id,
                document_title=c.document_title,
                content=c.content,
                score=c.score,
                page_number=c.page_number,
                grade=c.metadata.get("grade"),
                subject=c.metadata.get("subject"),
                chapter=c.metadata.get("chapter"),
                topic=c.metadata.get("topic"),
            )
            for c in validated.chunks
        ]

        usage = llm_response.usage
        observability = RagObservability(
            embedding_ms=round(retrieve_timing["embedding_ms"], 1),
            retrieval_ms=round(retrieve_timing["retrieval_ms"], 1),
            llm_ms=round(llm_ms, 1),
            total_ms=round(total_ms, 1),
            chunks_retrieved=len(raw_context.chunks),
            chunks_used=len(validated.chunks),
            similarity_scores=[round(c.score, 4) for c in validated.chunks],
            token_usage={
                "prompt_tokens": usage.prompt_tokens if usage else 0,
                "completion_tokens": usage.completion_tokens if usage else 0,
                "total_tokens": usage.total_tokens if usage else 0,
            },
        )

        logger.info(
            "rag_query_complete",
            query_len=len(request.query),
            curriculum=curriculum_payload,
            chunks_used=len(validated.chunks),
            has_context=validated.has_context,
            total_ms=round(total_ms, 1),
            llm_ms=round(llm_ms, 1),
            embedding_ms=round(retrieve_timing["embedding_ms"], 1),
            retrieval_ms=round(retrieve_timing["retrieval_ms"], 1),
            token_usage=observability.token_usage,
        )

        response = RagQueryResponse(
            query=request.query,
            answer=llm_response.content,
            has_context=validated.has_context,
            chunks=chunk_results if request.include_chunks else [],
            curriculum_filter=curriculum_payload,
            observability=observability,
        )

        if self._cache:
            await self._cache.set(request.query, cache_scope, response.model_dump(mode="json"))

        return response
