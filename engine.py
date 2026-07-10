"""
Learning Path Engine — Roognis AI (Phase 0.5)

Generates personalised learning paths by combining the knowledge graph
topology with the student's current mastery state.

Three capabilities:
  path_to_concept  — ordered unmastered prerequisites to reach a target concept
  get_frontier     — concepts ready to learn right now (prereqs met, not mastered)
  curriculum_coverage — % of each subject mastered
"""
from uuid import UUID

import structlog

from domain import (
    AbstractKnowledgeGraph,
    AbstractMasteryRepository,
    AbstractStudentProfileRepository,
    ConceptNode,
    RecommendationResponse,
)

logger = structlog.get_logger(__name__)

_MASTERY_THRESHOLD = 85.0
_READINESS_THRESHOLD = 0.5
_MAX_PATH_LENGTH = 10
_MAX_FRONTIER = 8


class LearningPathService:
    def __init__(
        self,
        graph: AbstractKnowledgeGraph,
        mastery_repo: AbstractMasteryRepository,
        profile_repo: AbstractStudentProfileRepository,
    ) -> None:
        self._graph = graph
        self._mastery = mastery_repo
        self._profiles = profile_repo

    async def path_to_concept(self, user_id: UUID, target_concept_id: UUID) -> list[ConceptNode]:
        mastery_records = await self._mastery.list_by_user(user_id)
        mastery_map: dict[UUID, float] = {r.concept_id: r.score for r in mastery_records}
        mastered_ids = {cid for cid, score in mastery_map.items() if score >= _MASTERY_THRESHOLD}

        all_prereqs = await self._graph.get_all_prerequisites(target_concept_id)
        unmastered = [n for n in all_prereqs if n.id not in mastered_ids]
        if not unmastered:
            return []

        ordered_ids = await self._graph.learning_order([n.id for n in unmastered])
        node_map = {n.id: n for n in unmastered}
        return [node_map[cid] for cid in ordered_ids if cid in node_map][:_MAX_PATH_LENGTH]

    async def get_frontier(self, user_id: UUID) -> list[RecommendationResponse]:
        profile = await self._profiles.get_by_user_id(user_id)
        if not profile or not profile.grade or not profile.subjects:
            return []

        mastery_records = await self._mastery.list_by_user(user_id)
        mastery_map: dict[UUID, float] = {r.concept_id: r.score for r in mastery_records}
        mastered_ids = {cid for cid, score in mastery_map.items() if score >= _MASTERY_THRESHOLD}

        frontier: list[RecommendationResponse] = []
        seen: set[UUID] = set()
        for subject in profile.subjects:
            for node in await self._graph.list_by_subject(subject, profile.grade):
                if node.id in mastered_ids or node.id in seen:
                    continue
                seen.add(node.id)
                readiness = await self._graph.readiness_for(node.id, mastery_map)
                if readiness < _READINESS_THRESHOLD:
                    continue
                current_score = mastery_map.get(node.id, 0.0)
                frontier.append(RecommendationResponse(
                    concept_id=node.id, concept_name=node.name,
                    subject=node.subject, chapter=node.chapter,
                    reason=_frontier_reason(readiness, current_score),
                    readiness_score=readiness,
                ))

        frontier.sort(key=lambda r: (-r.readiness_score, mastery_map.get(r.concept_id, 0.0)))
        return frontier[:_MAX_FRONTIER]

    async def curriculum_coverage(self, user_id: UUID) -> dict[str, dict]:
        profile = await self._profiles.get_by_user_id(user_id)
        if not profile or not profile.grade or not profile.subjects:
            return {}

        mastery_records = await self._mastery.list_by_user(user_id)
        mastered_ids = {r.concept_id for r in mastery_records if r.score >= _MASTERY_THRESHOLD}
        coverage: dict[str, dict] = {}
        for subject in profile.subjects:
            nodes = await self._graph.list_by_subject(subject, profile.grade)
            total = len(nodes)
            mastered = sum(1 for n in nodes if n.id in mastered_ids)
            coverage[subject] = {
                "total": total,
                "mastered": mastered,
                "coverage_pct": round(mastered / total * 100, 1) if total > 0 else 0.0,
            }
        return coverage


def _frontier_reason(readiness: float, current_score: float) -> str:
    if readiness == 1.0 and current_score == 0:
        return "All prerequisites mastered — ready to start."
    if readiness == 1.0:
        return f"All prerequisites mastered. Current score {current_score:.0f}/100 — reinforce."
    return f"{int(readiness * 100)}% prerequisites met. Current score {current_score:.0f}/100."
