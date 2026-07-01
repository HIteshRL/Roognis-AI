from uuid import UUID

import structlog

from src.application.dtos.learning import ConceptExtractionResult
from src.domain.entities.learning import LearningGap
from src.domain.repositories.learning_repository import (
    AbstractConceptNodeRepository,
    AbstractLearningGapRepository,
)

logger = structlog.get_logger(__name__)


class LearningGapDetector:
    def __init__(
        self,
        gap_repo: AbstractLearningGapRepository,
        concept_repo: AbstractConceptNodeRepository,
    ) -> None:
        self._gaps = gap_repo
        self._concepts = concept_repo

    async def process_extraction(
        self,
        user_id: UUID,
        extraction: ConceptExtractionResult,
        subject: str | None = None,
        grade: str | None = None,
        chapter: str | None = None,
    ) -> list[LearningGap]:
        if not extraction.misconceptions:
            return []

        updated_gaps: list[LearningGap] = []
        for misconception in extraction.misconceptions:
            concept_name = extraction.primary_concept
            node = await self._concepts.get_or_create(concept_name, subject, grade, chapter)

            reason = f"Misconception: {misconception}"
            gap = await self._gaps.get_or_create(user_id, node.id, node.name, reason)

            if gap.occurrence_count > 0:
                gap.increment()
                gap.reason = reason
                gap = await self._gaps.update(gap)
            else:
                gap = await self._gaps.update(gap)

            logger.info(
                "learning_gap_detected",
                user_id=str(user_id),
                concept=concept_name,
                severity=gap.severity,
                occurrences=gap.occurrence_count,
            )
            updated_gaps.append(gap)

        return updated_gaps

    async def list_gaps(
        self, user_id: UUID, include_resolved: bool = False
    ) -> list[LearningGap]:
        return await self._gaps.list_by_user(user_id, include_resolved=include_resolved)

    async def resolve(self, gap_id: UUID) -> None:
        await self._gaps.resolve(gap_id)
