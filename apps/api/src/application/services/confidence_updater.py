"""
ConfidenceUpdater — converts a single observation into coordinated state updates.

Given an evaluated question (or a chat-derived signal), it:
  1. snapshots assessment confidence BEFORE (from the evidence log),
  2. refines mastery, active gaps, and the recall schedule (never overwriting
     state wholesale — each is an incremental, evidence-weighted nudge),
  3. snapshots confidence AFTER,
  4. appends one immutable evidence event capturing the whole transition.

Fail-open: any sub-step failure is logged and swallowed so the caller (often the
background learning pipeline) is never broken by it.
"""
from uuid import UUID

import structlog

from src.application.services.evidence_collector import EvidenceCollector
from src.application.services.recall_scheduler import RecallScheduler
from src.domain.entities.question import GeneratedQuestion, LearnerEvidence, signal_polarity
from src.domain.repositories.learning_repository import (
    AbstractConceptNodeRepository,
    AbstractLearningGapRepository,
    AbstractMasteryRepository,
)

logger = structlog.get_logger(__name__)


class ConfidenceUpdater:
    def __init__(
        self,
        evidence_collector: EvidenceCollector,
        recall_scheduler: RecallScheduler,
        mastery_repo: AbstractMasteryRepository,
        concept_repo: AbstractConceptNodeRepository,
        gap_repo: AbstractLearningGapRepository | None = None,
    ) -> None:
        self._evidence = evidence_collector
        self._recall = recall_scheduler
        self._mastery = mastery_repo
        self._concepts = concept_repo
        self._gaps = gap_repo

    async def apply_question_result(self, question: GeneratedQuestion) -> LearnerEvidence:
        """Fold an evaluated question into learner state and log the evidence."""
        return await self.apply_signal(
            user_id=question.user_id,
            concept_id=question.concept_id,
            concept_name=question.concept_name,
            signal=question.signal,
            objective=question.objective,
            source="question",
            weight=question.evidence_weight,
            bloom_level=question.bloom_level,
            question_id=question.id,
            detail=question.feedback,
        )

    async def apply_signal(
        self,
        user_id: UUID,
        concept_id: UUID,
        concept_name: str,
        signal: str,
        objective: str = "verify_mastery",
        source: str = "question",
        weight: float = 1.0,
        bloom_level: str = "Understand",
        intent: str = "unknown",
        question_id: UUID | None = None,
        detail: str = "",
    ) -> LearnerEvidence:
        polarity = signal_polarity(signal)

        confidence_before = await self._evidence.concept_confidence(user_id, concept_id)

        # ── Mastery: incremental nudge, reusing the smoothed EMA on the entity ──
        try:
            record = await self._mastery.get_or_create(user_id, concept_id, concept_name)
            record.apply_interaction(bloom_level, has_misconception=(polarity < 0))
            await self._mastery.update(record)
        except Exception as exc:
            logger.warning("confidence_mastery_update_failed", concept=concept_name, error=str(exc))

        # ── Gaps: verified-correct heals, verified-wrong escalates ──────────────
        if self._gaps is not None:
            try:
                await self._update_gap(user_id, concept_id, concept_name, polarity, signal)
            except Exception as exc:
                logger.warning("confidence_gap_update_failed", concept=concept_name, error=str(exc))

        # ── Recall schedule: reschedule based on outcome quality ────────────────
        try:
            await self._recall.record_signal(user_id, concept_id, concept_name, signal)
        except Exception as exc:
            logger.warning("confidence_recall_update_failed", concept=concept_name, error=str(exc))

        # ── Evidence event capturing before/after (written last, after state) ───
        # Fold this signal into the "after" reading so the event reflects the state
        # it produces — the event itself is not yet in the log at this point.
        confidence_after = await self._evidence.concept_confidence(
            user_id, concept_id, extra=[(signal, weight)]
        )
        return await self._evidence.record(
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

    async def _update_gap(
        self, user_id: UUID, concept_id: UUID, concept_name: str, polarity: float, signal: str
    ) -> None:
        if polarity < 0:
            reason = f"Verified via questioning: {signal}"
            gap = await self._gaps.get_or_create(user_id, concept_id, concept_name, reason)
            gap.increment()
            await self._gaps.update(gap)
        elif polarity > 0:
            # A confirmed-correct answer is evidence to heal any open gap here.
            existing = await self._gaps.list_by_user(user_id, include_resolved=False)
            for gap in existing:
                if gap.concept_id == concept_id:
                    await self._gaps.resolve(gap.id)
