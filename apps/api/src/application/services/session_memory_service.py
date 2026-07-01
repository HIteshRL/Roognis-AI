from uuid import UUID

import structlog

from src.application.dtos.learning import ConceptExtractionResult
from src.domain.entities.learning import LearningSession
from src.domain.repositories.learning_repository import AbstractLearningSessionRepository

logger = structlog.get_logger(__name__)


class SessionMemoryService:
    def __init__(self, repo: AbstractLearningSessionRepository) -> None:
        self._repo = repo

    async def record(
        self,
        user_id: UUID,
        question: str,
        ai_response: str,
        extraction: ConceptExtractionResult,
        conversation_id: UUID | None = None,
        subject: str | None = None,
        chapter: str | None = None,
        grade: str | None = None,
        retrieved_context: str | None = None,
        token_count: int = 0,
        duration_ms: int = 0,
    ) -> LearningSession:
        session = LearningSession(
            user_id=user_id,
            question=question,
            ai_response=ai_response,
            conversation_id=conversation_id,
            subject=subject,
            chapter=chapter,
            grade=grade,
            retrieved_context=retrieved_context,
            primary_concept=extraction.primary_concept,
            concepts_discussed=extraction.secondary_concepts,
            skills=extraction.skills,
            bloom_level=extraction.bloom_level,
            difficulty_level=extraction.difficulty,
            misconceptions=extraction.misconceptions,
            token_count=token_count,
            duration_ms=duration_ms,
        )
        saved = await self._repo.create(session)
        logger.info(
            "learning_session_recorded",
            user_id=str(user_id),
            concept=extraction.primary_concept,
            bloom=extraction.bloom_level,
        )
        return saved

    async def list_sessions(
        self, user_id: UUID, limit: int = 20, offset: int = 0
    ) -> tuple[list[LearningSession], int]:
        sessions = await self._repo.list_by_user(user_id, limit=limit, offset=offset)
        total = await self._repo.count_by_user(user_id)
        return sessions, total

    async def recent_concepts(self, user_id: UUID, days: int = 7) -> list[str]:
        return await self._repo.recent_concepts(user_id, days=days)
