import structlog

from src.application.dtos.knowledge import RetrievedContext

logger = structlog.get_logger(__name__)

_MIN_CONTENT_LENGTH = 50
_MIN_SCORE = 0.35


class ContextValidationService:
    """
    Validates retrieved context quality before it reaches the LLM.
    Filters out low-quality chunks to prevent hallucination-inducing noise.
    """

    def __init__(self, min_score: float = _MIN_SCORE) -> None:
        self._min_score = min_score

    def validate(self, context: RetrievedContext) -> RetrievedContext:
        valid_chunks = [
            chunk
            for chunk in context.chunks
            if chunk.score >= self._min_score
            and len(chunk.content.strip()) >= _MIN_CONTENT_LENGTH
        ]

        if len(valid_chunks) < len(context.chunks):
            logger.info(
                "context_filtered",
                original=len(context.chunks),
                valid=len(valid_chunks),
            )

        return RetrievedContext(
            chunks=valid_chunks,
            has_context=bool(valid_chunks),
            query=context.query,
        )
