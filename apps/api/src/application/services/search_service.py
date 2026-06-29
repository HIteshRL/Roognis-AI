import structlog

from src.application.dtos.knowledge import SearchRequest, SearchResponse
from src.application.services.context_validation_service import ContextValidationService
from src.application.services.retrieval_service import RetrievalService

logger = structlog.get_logger(__name__)


class SearchService:
    """Public-facing search used by the admin Search Playground and student debug panel."""

    def __init__(
        self,
        retrieval_svc: RetrievalService,
        validation_svc: ContextValidationService,
    ) -> None:
        self._retrieval = retrieval_svc
        self._validation = validation_svc

    async def search(self, request: SearchRequest) -> SearchResponse:
        context = await self._retrieval.retrieve(
            query=request.query,
            knowledge_base_id=request.knowledge_base_id,
            top_k=request.top_k,
            score_threshold=request.score_threshold,
        )
        validated = self._validation.validate(context)

        return SearchResponse(
            query=request.query,
            results=validated.chunks,
            total_found=len(validated.chunks),
            knowledge_base_id=request.knowledge_base_id,
        )
