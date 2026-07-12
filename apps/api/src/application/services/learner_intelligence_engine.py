"""
LearnerIntelligenceEngine — assembles the unified, evidence-derived LearnerContext.

This is the read-side aggregator for the whole subsystem. It composes existing
signals (mastery, gaps, teaching memory, recommendations) with the new
evidence-driven ones (inferred preferences, recall/retention state) into a single
LearnerContext object:

  {weak_concepts, persistent_gaps, preferences, current_goal, memory_state, recommendations}

It performs no inference of its own beyond selection/derivation — all state is
already refined from accumulated evidence by the writing services. Every sub-read
is fail-open so a partial signal never blanks the whole context.
"""
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID

import structlog

from src.application.services.preference_inference_engine import PreferenceInferenceEngine
from src.application.services.recall_scheduler import RecallScheduler
from src.domain.repositories.learning_repository import (
    AbstractLearningGapRepository,
    AbstractMasteryRepository,
)

logger = structlog.get_logger(__name__)

_WEAK_MASTERY = 60.0
_MAX_ITEMS = 5


# Narrow structural interfaces (ISP): the engine depends only on the one method it
# calls on each optional collaborator, not on the concrete service. Structural
# typing keeps this decoupled without importing those services (no circular import).
class StrugglingConceptsSource(Protocol):
    async def get_struggling_concepts(self, user_id: UUID) -> list: ...


class ConceptRecommender(Protocol):
    async def recommend(self, user_id: UUID) -> list: ...


@dataclass
class LearnerContext:
    user_id: UUID
    weak_concepts: list[dict] = field(default_factory=list)
    persistent_gaps: list[dict] = field(default_factory=list)
    preferences: list[dict] = field(default_factory=list)
    current_goal: dict | None = None
    memory_state: dict = field(default_factory=dict)
    recommendations: list[dict] = field(default_factory=list)


class LearnerIntelligenceEngine:
    def __init__(
        self,
        mastery_repo: AbstractMasteryRepository,
        gap_repo: AbstractLearningGapRepository,
        preference_engine: PreferenceInferenceEngine,
        recall_scheduler: RecallScheduler,
        concept_memory_svc: StrugglingConceptsSource | None = None,
        recommender: ConceptRecommender | None = None,
    ) -> None:
        self._mastery = mastery_repo
        self._gaps = gap_repo
        self._preferences = preference_engine
        self._recall = recall_scheduler
        self._concept_memory = concept_memory_svc
        self._recommender = recommender

    async def build_context(self, user_id: UUID, now: datetime | None = None) -> LearnerContext:
        now = now or datetime.now(UTC)
        ctx = LearnerContext(user_id=user_id)

        ctx.weak_concepts = await self._weak_concepts(user_id)
        ctx.persistent_gaps = await self._persistent_gaps(user_id)
        ctx.preferences = await self._preferences_list(user_id)
        ctx.memory_state = await self._memory_state(user_id, now)
        ctx.recommendations = await self._recommendations(user_id)
        ctx.current_goal = ctx.recommendations[0] if ctx.recommendations else None
        return ctx

    async def _weak_concepts(self, user_id: UUID) -> list[dict]:
        try:
            records = await self._mastery.list_by_user(user_id)
        except Exception as exc:
            logger.warning("intel_weak_concepts_failed", error=str(exc))
            return []
        weak = [r for r in records if r.score < _WEAK_MASTERY]
        weak.sort(key=lambda r: r.score)
        return [
            {"concept_id": str(r.concept_id), "concept_name": r.concept_name,
             "score": r.score, "label": r.label}
            for r in weak[:_MAX_ITEMS]
        ]

    async def _persistent_gaps(self, user_id: UUID) -> list[dict]:
        try:
            gaps = await self._gaps.list_by_user(user_id, include_resolved=False)
        except Exception as exc:
            logger.warning("intel_gaps_failed", error=str(exc))
            return []
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        gaps.sort(key=lambda g: (severity_order.get(g.severity, 3), -g.occurrence_count))
        return [
            {"concept_id": str(g.concept_id), "concept_name": g.concept_name,
             "severity": g.severity, "confidence": g.confidence,
             "occurrence_count": g.occurrence_count, "reason": g.reason}
            for g in gaps[:_MAX_ITEMS]
        ]

    async def _preferences_list(self, user_id: UUID) -> list[dict]:
        try:
            prefs = await self._preferences.reliable_preferences(user_id)
        except Exception as exc:
            logger.warning("intel_preferences_failed", error=str(exc))
            return []
        return [
            {"dimension": p.dimension, "strength": p.strength,
             "confidence": p.confidence, "evidence_count": p.evidence_count}
            for p in prefs[:_MAX_ITEMS]
        ]

    async def _memory_state(self, user_id: UUID, now: datetime) -> dict:
        state: dict = {"struggling_concepts": [], "due_for_recall": 0, "at_risk": []}
        if self._concept_memory is not None:
            try:
                struggling = await self._concept_memory.get_struggling_concepts(user_id)
                state["struggling_concepts"] = [
                    {"concept_name": m.concept_name, "times_taught": m.times_taught,
                     "success_rate": m.success_rate}
                    for m in struggling[:_MAX_ITEMS]
                ]
            except Exception as exc:
                logger.warning("intel_memory_failed", error=str(exc))
        try:
            due = await self._recall.due(user_id, now)
            state["due_for_recall"] = len(due)
            at_risk = await self._recall.at_risk(user_id, now=now)
            state["at_risk"] = [
                {"concept_name": s.concept_name, "retention": retention}
                for s, retention in at_risk[:_MAX_ITEMS]
            ]
        except Exception as exc:
            logger.warning("intel_recall_failed", error=str(exc))
        return state

    async def _recommendations(self, user_id: UUID) -> list[dict]:
        if self._recommender is None:
            return []
        try:
            recs = await self._recommender.recommend(user_id)
        except Exception as exc:
            logger.warning("intel_recommendations_failed", error=str(exc))
            return []
        return [
            {"concept_id": str(r.concept_id), "concept_name": r.concept_name,
             "reason": r.reason, "readiness_score": r.readiness_score}
            for r in recs[:_MAX_ITEMS]
        ]
