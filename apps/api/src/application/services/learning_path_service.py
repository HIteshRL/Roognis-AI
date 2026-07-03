"""
Phase 0.5: Learning Path Service.

Generates personalized learning paths for a student by combining the
knowledge graph topology with their current mastery state. Provides:

  path_to_concept(user_id, target_concept_id)
      — ordered sequence of prerequisite concepts to learn before target

  get_frontier(user_id)
      — concepts ready to learn right now (prereqs met, not yet mastered)

  curriculum_coverage(user_id)
      — % of each subject's concepts that are mastered
"""
from uuid import UUID

import structlog

from src.application.dtos.learning import RecommendationResponse
from src.application.services.knowledge_graph_service import KnowledgeGraphService
from src.domain.entities.learning import ConceptNode
from src.domain.repositories.learning_repository import (
    AbstractMasteryRepository,
    AbstractStudentProfileRepository,
)

logger = structlog.get_logger(__name__)

_MASTERY_THRESHOLD = 85.0
_READINESS_THRESHOLD = 0.5
_MAX_PATH_LENGTH = 10
_MAX_FRONTIER = 8


class LearningPathService:
    def __init__(
        self,
        graph: KnowledgeGraphService,
        mastery_repo: AbstractMasteryRepository,
        profile_repo: AbstractStudentProfileRepository,
    ) -> None:
        self._graph = graph
        self._mastery = mastery_repo
        self._profiles = profile_repo

    async def path_to_concept(
        self, user_id: UUID, target_concept_id: UUID
    ) -> list[ConceptNode]:
        """
        Returns the ordered list of concepts to learn before the target concept.
        Only includes concepts not yet mastered by the student.
        """
        mastery_records = await self._mastery.list_by_user(user_id)
        mastery_map: dict[UUID, float] = {r.concept_id: r.score for r in mastery_records}
        mastered_ids = {cid for cid, score in mastery_map.items() if score >= _MASTERY_THRESHOLD}

        # Get all prerequisite nodes (transitive)
        all_prereqs = await self._graph.get_all_prerequisites(target_concept_id)

        # Filter to unmastered prerequisites only
        unmastered = [n for n in all_prereqs if n.id not in mastered_ids]

        if not unmastered:
            return []

        # Order them topologically
        ordered_ids = await self._graph.learning_order([n.id for n in unmastered])
        node_map = {n.id: n for n in unmastered}
        ordered = [node_map[cid] for cid in ordered_ids if cid in node_map]
        return ordered[:_MAX_PATH_LENGTH]

    async def get_frontier(self, user_id: UUID) -> list[RecommendationResponse]:
        """
        Concepts the student is ready to learn: prerequisites sufficiently mastered
        (>= 50% readiness) but target itself not yet mastered.
        """
        profile = await self._profiles.get_by_user_id(user_id)
        if not profile or not profile.grade or not profile.subjects:
            return []

        mastery_records = await self._mastery.list_by_user(user_id)
        mastery_map: dict[UUID, float] = {r.concept_id: r.score for r in mastery_records}
        mastered_ids = {cid for cid, score in mastery_map.items() if score >= _MASTERY_THRESHOLD}

        frontier: list[RecommendationResponse] = []
        seen: set[UUID] = set()

        for subject in profile.subjects:
            nodes = await self._graph.list_by_subject(subject, profile.grade)
            for node in nodes:
                if node.id in mastered_ids or node.id in seen:
                    continue
                seen.add(node.id)
                readiness = await self._graph.readiness_for(node.id, mastery_map)
                if readiness < _READINESS_THRESHOLD:
                    continue
                current_score = mastery_map.get(node.id, 0.0)
                frontier.append(
                    RecommendationResponse(
                        concept_id=node.id,
                        concept_name=node.name,
                        subject=node.subject,
                        chapter=node.chapter,
                        reason=_frontier_reason(readiness, current_score),
                        readiness_score=readiness,
                    )
                )

        frontier.sort(key=lambda r: (-r.readiness_score, mastery_map.get(r.concept_id, 0.0)))
        return frontier[:_MAX_FRONTIER]

    async def curriculum_coverage(self, user_id: UUID) -> dict[str, dict]:
        """
        Returns coverage breakdown by subject: {subject: {total, mastered, pct}}.
        """
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
            pct = round(mastered / total * 100, 1) if total > 0 else 0.0
            coverage[subject] = {"total": total, "mastered": mastered, "coverage_pct": pct}

        return coverage


def _frontier_reason(readiness: float, current_score: float) -> str:
    if readiness == 1.0 and current_score == 0:
        return "All prerequisites mastered — ready to start."
    if readiness == 1.0:
        return f"All prerequisites mastered. Current score {current_score:.0f}/100 — reinforce."
    pct = int(readiness * 100)
    if current_score == 0:
        return f"{pct}% of prerequisites mastered — good time to begin."
    return f"{pct}% prerequisites met. Current score {current_score:.0f}/100."
