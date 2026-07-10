"""
EvidenceCollector — the write + read side of the event-sourced evidence log.

Evidence is append-only: every observation about the learner is a fact we keep
forever. Assessment *confidence* (our certainty about the learner's state for a
concept) is derived from that log, never stored redundantly — high when many
consistent observations agree, low when evidence is sparse or contradictory.
"""
from uuid import UUID

import structlog

from src.domain.entities.question import LearnerEvidence, signal_polarity
from src.domain.repositories.question_repository import AbstractEvidenceRepository

logger = structlog.get_logger(__name__)

_CONFIDENCE_SATURATION = 4.0   # observations before coverage tops out


def _confidence_from(pairs: list[tuple[str, float]]) -> float:
    """agreement × coverage over (signal, weight) pairs. Pure — easy to unit-test."""
    directional = [(s, w) for s, w in pairs if signal_polarity(s) != 0]
    if not directional:
        return 0.0
    pos = sum(w for s, w in directional if signal_polarity(s) > 0)
    neg = sum(w for s, w in directional if signal_polarity(s) < 0)
    total = pos + neg
    if total <= 0:
        return 0.0
    agreement = abs(pos - neg) / total
    coverage = min(1.0, len(directional) / _CONFIDENCE_SATURATION)
    return round(agreement * coverage, 4)


class EvidenceCollector:
    def __init__(self, evidence_repo: AbstractEvidenceRepository) -> None:
        self._evidence = evidence_repo

    async def record(
        self,
        user_id: UUID,
        signal: str,
        concept_id: UUID | None = None,
        concept_name: str | None = None,
        objective: str = "verify_mastery",
        source: str = "question",
        weight: float = 1.0,
        bloom_level: str = "Understand",
        intent: str = "unknown",
        question_id: UUID | None = None,
        confidence_before: float = 0.0,
        confidence_after: float = 0.0,
        detail: str = "",
    ) -> LearnerEvidence:
        evidence = LearnerEvidence(
            user_id=user_id,
            signal=signal,
            concept_id=concept_id,
            concept_name=concept_name,
            objective=objective,
            source=source,
            weight=weight,
            bloom_level=bloom_level,
            intent=intent,
            question_id=question_id,
            confidence_before=confidence_before,
            confidence_after=confidence_after,
            detail=detail,
        )
        return await self._evidence.add(evidence)

    async def concept_confidence(
        self,
        user_id: UUID,
        concept_id: UUID,
        extra: list[tuple[str, float]] | None = None,
    ) -> float:
        """Certainty (0..1) about the learner's state for this concept.

        confidence = agreement × coverage:
          - coverage grows with the number of observations (saturates at 1.0)
          - agreement is how one-sided the weighted signals are (contradiction → 0)

        ``extra`` folds in an in-flight (signal, weight) not yet persisted — used to
        compute the post-event confidence to stamp on the event being written.
        """
        events = await self._evidence.list_by_concept(user_id, concept_id, limit=50)
        pairs = [(e.signal, e.weight) for e in events]
        if extra:
            pairs.extend(extra)
        return _confidence_from(pairs)

    async def verification_count(self, user_id: UUID, concept_id: UUID) -> int:
        return await self._evidence.count_by_concept(user_id, concept_id)

    async def recent(self, user_id: UUID, limit: int = 50) -> list[LearnerEvidence]:
        return await self._evidence.list_by_user(user_id, limit=limit)
