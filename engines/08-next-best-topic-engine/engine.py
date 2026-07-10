"""
Next Best Topic Engine — Roognis AI

Recommends the optimal next concept(s) to study. Considers:
  - Prerequisite readiness (>= 50% of prereqs mastered)
  - Current mastery score (low score + high readiness = high priority)
  - Subjects from the student's profile

Returns up to 5 `RecommendationResponse` objects sorted by priority.
"""
from uuid import UUID

import structlog

from domain import (
    AbstractKnowledgeGraph,
    AbstractMasteryRepository,
    AbstractStudentProfileRepository,
    RecommendationResponse,
)

logger = structlog.get_logger(__name__)

_MAX_RECOMMENDATIONS = 5


class NextBestTopicEngine:
    def __init__(
        self,
        graph: AbstractKnowledgeGraph,
        mastery_repo: AbstractMasteryRepository,
        profile_repo: AbstractStudentProfileRepository,
    ) -> None:
        self._graph = graph
        self._mastery = mastery_repo
        self._profiles = profile_repo

    async def recommend(self, user_id: UUID) -> list[RecommendationResponse]:
        profile = await self._profiles.get_by_user_id(user_id)
        if not profile or not profile.grade or not profile.subjects:
            return []

        mastery_records = await self._mastery.list_by_user(user_id)
        mastery_map: dict[UUID, float] = {r.concept_id: r.score for r in mastery_records}
        mastered_ids = {cid for cid, score in mastery_map.items() if score >= 85}

        candidates: list[RecommendationResponse] = []
        for subject in profile.subjects:
            for node in await self._graph.list_by_subject(subject, profile.grade):
                if node.id in mastered_ids:
                    continue
                current_score = mastery_map.get(node.id, 0.0)
                readiness = await self._graph.readiness_for(node.id, mastery_map)
                if readiness < 0.5:
                    continue
                candidates.append(RecommendationResponse(
                    concept_id=node.id, concept_name=node.name,
                    subject=node.subject, chapter=node.chapter,
                    reason=_build_reason(current_score, readiness),
                    readiness_score=readiness,
                ))

        candidates.sort(key=lambda r: (-r.readiness_score, mastery_map.get(r.concept_id, 0.0)))
        return candidates[:_MAX_RECOMMENDATIONS]


def _build_reason(current_score: float, readiness: float) -> str:
    if current_score == 0:
        return "New concept — all prerequisites met."
    if readiness == 1.0:
        return f"All prerequisites mastered. Current score {current_score:.0f}/100."
    return f"{int(readiness * 100)}% of prerequisites mastered. Current score {current_score:.0f}/100."
