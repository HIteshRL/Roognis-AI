from uuid import UUID

import structlog

from src.domain.entities.learning import ConceptEdge, ConceptNode
from src.domain.repositories.learning_repository import (
    AbstractConceptEdgeRepository,
    AbstractConceptNodeRepository,
)

logger = structlog.get_logger(__name__)


class KnowledgeGraphService:
    def __init__(
        self,
        node_repo: AbstractConceptNodeRepository,
        edge_repo: AbstractConceptEdgeRepository,
    ) -> None:
        self._nodes = node_repo
        self._edges = edge_repo

    async def get_or_create_node(
        self,
        name: str,
        subject: str | None = None,
        grade: str | None = None,
        chapter: str | None = None,
    ) -> ConceptNode:
        return await self._nodes.get_or_create(name, subject, grade, chapter)

    async def add_prerequisite(
        self, source_id: UUID, target_id: UUID, weight: float = 1.0
    ) -> ConceptEdge | None:
        if await self._edges.exists(source_id, target_id):
            return None
        edge = ConceptEdge(source_id=source_id, target_id=target_id, weight=weight)
        return await self._edges.create(edge)

    async def get_prerequisites(self, concept_id: UUID) -> list[ConceptNode]:
        return await self._edges.get_prerequisites(concept_id)

    async def get_successors(self, concept_id: UUID) -> list[ConceptNode]:
        return await self._edges.get_successors(concept_id)

    async def list_by_subject(self, subject: str, grade: str) -> list[ConceptNode]:
        return await self._nodes.list_by_subject_grade(subject, grade)

    async def readiness_for(
        self,
        concept_id: UUID,
        mastery_map: dict[UUID, float],
    ) -> float:
        """
        Returns 0–1: fraction of prerequisites that are mastered (≥70 score).
        A concept with no prerequisites is always fully ready (1.0).
        """
        prereqs = await self._edges.get_prerequisites(concept_id)
        if not prereqs:
            return 1.0
        ready = sum(1 for p in prereqs if mastery_map.get(p.id, 0.0) >= 70)
        return round(ready / len(prereqs), 3)
