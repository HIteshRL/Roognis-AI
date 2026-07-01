from uuid import UUID

import structlog

from src.application.dtos.learning import ConceptExtractionResult
from src.domain.repositories.learning_repository import (
    AbstractConceptNodeRepository,
    AbstractMasteryRepository,
)

logger = structlog.get_logger(__name__)


class MasteryEngine:
    def __init__(
        self,
        mastery_repo: AbstractMasteryRepository,
        concept_repo: AbstractConceptNodeRepository,
    ) -> None:
        self._mastery = mastery_repo
        self._concepts = concept_repo

    async def update_from_extraction(
        self,
        user_id: UUID,
        extraction: ConceptExtractionResult,
        subject: str | None = None,
        grade: str | None = None,
        chapter: str | None = None,
    ) -> None:
        has_misconception = len(extraction.misconceptions) > 0

        all_concepts = [extraction.primary_concept] + extraction.secondary_concepts
        for concept_name in all_concepts:
            if not concept_name or not concept_name.strip():
                continue
            node = await self._concepts.get_or_create(concept_name, subject, grade, chapter)
            record = await self._mastery.get_or_create(user_id, node.id, node.name)
            record.apply_interaction(extraction.bloom_level, has_misconception)
            await self._mastery.update(record)
            logger.debug(
                "mastery_updated",
                user_id=str(user_id),
                concept=concept_name,
                score=record.score,
                label=record.label,
            )

    async def get_all(self, user_id: UUID):
        return await self._mastery.list_by_user(user_id)

    async def average(self, user_id: UUID) -> float:
        return await self._mastery.average_score(user_id)
