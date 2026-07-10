"""
Concept Memory Engine — Roognis AI (Phase 0.5)

Tracks per-concept pedagogical teaching history across sessions.
For each concept a student encounters, records how many times it was taught,
whether explanations succeeded or failed, and which approach was used.

The LearnerContextService reads this memory to warn the LLM when a concept
has repeatedly failed so it can try a different strategy (procedural vs conceptual).
"""
from uuid import UUID

import structlog

from domain import (
    BLOOM_LEVELS,
    AbstractConceptMemoryRepository,
    AbstractConceptNodeRepository,
    ConceptExtractionResult,
    ConceptMemory,
)

logger = structlog.get_logger(__name__)

_CONCEPTUAL_THRESHOLD = 3


def _approach_from_bloom(bloom_level: str) -> str:
    rank = BLOOM_LEVELS.index(bloom_level) if bloom_level in BLOOM_LEVELS else 1
    return "conceptual" if rank >= _CONCEPTUAL_THRESHOLD else "procedural"


class ConceptMemoryService:
    def __init__(
        self,
        memory_repo: AbstractConceptMemoryRepository,
        concept_repo: AbstractConceptNodeRepository,
    ) -> None:
        self._memory = memory_repo
        self._concepts = concept_repo

    async def record_from_extraction(
        self,
        user_id: UUID,
        extraction: ConceptExtractionResult,
        subject: str | None = None,
        grade: str | None = None,
        chapter: str | None = None,
    ) -> None:
        had_misconception = len(extraction.misconceptions) > 0
        approach = _approach_from_bloom(extraction.bloom_level)
        note = extraction.misconceptions[0] if had_misconception else None

        for name in [extraction.primary_concept] + extraction.secondary_concepts:
            if not name or not name.strip():
                continue
            try:
                node = await self._concepts.get_or_create(name, subject, grade, chapter)
                mem = await self._memory.get_or_create(user_id, node.id, node.name)
                mem.record_interaction(approach, had_misconception, note)
                await self._memory.update(mem)
            except Exception as exc:
                logger.warning("concept_memory_record_failed", concept=name, error=str(exc))

    async def get_all(self, user_id: UUID) -> list[ConceptMemory]:
        return await self._memory.list_by_user(user_id)

    async def get_struggling_concepts(self, user_id: UUID, min_attempts: int = 3) -> list[ConceptMemory]:
        all_memories = await self._memory.list_by_user(user_id)
        return [m for m in all_memories if m.times_taught >= min_attempts and m.needs_different_approach]
