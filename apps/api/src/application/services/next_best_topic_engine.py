from uuid import UUID

import structlog

from src.application.dtos.learning import RecommendationResponse
from src.application.services.knowledge_graph_service import KnowledgeGraphService
from src.domain.repositories.learning_repository import (
    AbstractMasteryRepository,
    AbstractStudentProfileRepository,
)

logger = structlog.get_logger(__name__)

_MAX_RECOMMENDATIONS = 5


class NextBestTopicEngine:
    def __init__(
        self,
        graph: KnowledgeGraphService,
        mastery_repo: AbstractMasteryRepository,
        profile_repo: AbstractStudentProfileRepository,
    ) -> None:
        self._graph = graph
        self._mastery = mastery_repo
        self._profiles = profile_repo

    async def recommend(self, user_id: UUID) -> list[RecommendationResponse]:
        profile = await self._profiles.get_by_user_id(user_id)
        if not profile or not profile.grade:
            return []

        subjects = profile.subjects or []
        if not subjects:
            return []

        mastery_records = await self._mastery.list_by_user(user_id)
        mastery_map: dict[UUID, float] = {r.concept_id: r.score for r in mastery_records}
        mastered_ids = {cid for cid, score in mastery_map.items() if score >= 85}

        candidates: list[RecommendationResponse] = []

        for subject in subjects:
            nodes = await self._graph.list_by_subject(subject, profile.grade)
            for node in nodes:
                if node.id in mastered_ids:
                    continue
                current_score = mastery_map.get(node.id, 0.0)
                readiness = await self._graph.readiness_for(node.id, mastery_map)

                if readiness < 0.5:
                    continue  # prerequisites not yet met

                reason = _build_reason(current_score, readiness)
                candidates.append(
                    RecommendationResponse(
                        concept_id=node.id,
                        concept_name=node.name,
                        subject=node.subject,
                        chapter=node.chapter,
                        reason=reason,
                        readiness_score=readiness,
                    )
                )

        # Sort by readiness desc, then by current mastery asc (prioritise low-score ready concepts)
        candidates.sort(key=lambda r: (-r.readiness_score, mastery_map.get(r.concept_id, 0.0)))
        return candidates[:_MAX_RECOMMENDATIONS]


def _build_reason(current_score: float, readiness: float) -> str:
    if current_score == 0:
        return "New concept — all prerequisites met."
    if readiness == 1.0:
        return f"All prerequisites mastered. Current score {current_score:.0f}/100."
    pct = int(readiness * 100)
    return f"{pct}% of prerequisites mastered. Current score {current_score:.0f}/100."
