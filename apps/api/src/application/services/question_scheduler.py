"""
QuestionScheduler — decides WHAT to ask next to reduce learner uncertainty most.

It does not generate questions; it chooses a target (concept + objective) by
weighing the sources of uncertainty in priority order:
  1. a recall that is due            → verify_retention
  2. an active, escalating gap       → verify_gap
  3. a concept we're unsure about    → verify_confidence  (low evidence confidence)
  4. weak mastery                    → verify_mastery
Returns None when there is nothing worth asking (state is already certain).
"""
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

import structlog

from src.application.services.evidence_collector import EvidenceCollector
from src.application.services.recall_scheduler import RecallScheduler
from src.domain.repositories.learning_repository import (
    AbstractConceptNodeRepository,
    AbstractLearningGapRepository,
    AbstractMasteryRepository,
)

logger = structlog.get_logger(__name__)

_WEAK_MASTERY = 60.0
_LOW_CONFIDENCE = 0.5
_MIN_INTERACTIONS_FOR_CONFIDENCE_CHECK = 1


@dataclass
class QuestionTarget:
    concept_id: UUID
    concept_name: str
    objective: str
    bloom_level: str
    difficulty: str
    mastery_score: float
    reason: str


class QuestionScheduler:
    def __init__(
        self,
        mastery_repo: AbstractMasteryRepository,
        recall_scheduler: RecallScheduler,
        evidence_collector: EvidenceCollector,
        concept_repo: AbstractConceptNodeRepository,
        gap_repo: AbstractLearningGapRepository | None = None,
    ) -> None:
        self._mastery = mastery_repo
        self._recall = recall_scheduler
        self._evidence = evidence_collector
        self._concepts = concept_repo
        self._gaps = gap_repo

    async def next_target(
        self, user_id: UUID, now: datetime | None = None
    ) -> QuestionTarget | None:
        now = now or datetime.now(UTC)

        # 1. Retention — a due recall is the most time-sensitive uncertainty.
        due = await self._recall.due(user_id, now)
        if due:
            s = due[0]
            bloom, difficulty = await self._concept_traits(s.concept_id)
            return QuestionTarget(
                concept_id=s.concept_id,
                concept_name=s.concept_name,
                objective="verify_retention",
                bloom_level=bloom,
                difficulty=difficulty,
                mastery_score=0.0,
                reason=f"Recall due (last reviewed interval {s.interval_days}d)",
            )

        # 2. Active gaps — verify whether a suspected misconception is still real.
        if self._gaps is not None:
            gaps = await self._gaps.list_by_user(user_id, include_resolved=False)
            severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
            gaps.sort(key=lambda g: severity_order.get(g.severity, 3))
            if gaps:
                g = gaps[0]
                bloom, difficulty = await self._concept_traits(g.concept_id)
                return QuestionTarget(
                    concept_id=g.concept_id,
                    concept_name=g.concept_name,
                    objective="verify_gap",
                    bloom_level=bloom,
                    difficulty=difficulty,
                    mastery_score=0.0,
                    reason=f"{g.severity} gap ({g.occurrence_count}x): {g.reason}",
                )

        # 3 & 4. Scan mastery records for low confidence, then weak scores.
        records = await self._mastery.list_by_user(user_id)
        weak_candidate: QuestionTarget | None = None
        for r in sorted(records, key=lambda x: x.score):
            bloom, difficulty = await self._concept_traits(r.concept_id)

            if r.interaction_count >= _MIN_INTERACTIONS_FOR_CONFIDENCE_CHECK:
                confidence = await self._evidence.concept_confidence(user_id, r.concept_id)
                if confidence < _LOW_CONFIDENCE:
                    return QuestionTarget(
                        concept_id=r.concept_id,
                        concept_name=r.concept_name,
                        objective="verify_confidence",
                        bloom_level=bloom,
                        difficulty=difficulty,
                        mastery_score=r.score,
                        reason=f"Low assessment confidence ({confidence:.2f})",
                    )

            if weak_candidate is None and r.score < _WEAK_MASTERY:
                weak_candidate = QuestionTarget(
                    concept_id=r.concept_id,
                    concept_name=r.concept_name,
                    objective="verify_mastery",
                    bloom_level=bloom,
                    difficulty=difficulty,
                    mastery_score=r.score,
                    reason=f"Weak mastery (score {r.score:.0f})",
                )

        return weak_candidate

    async def _concept_traits(self, concept_id: UUID) -> tuple[str, str]:
        try:
            node = await self._concepts.get_by_id(concept_id)
            if node:
                return node.bloom_level, node.difficulty
        except Exception:
            pass
        return "Understand", "medium"
