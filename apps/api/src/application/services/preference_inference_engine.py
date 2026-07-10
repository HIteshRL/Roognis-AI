"""
PreferenceInferenceEngine — infers learning-style preferences from evidence.

Preferences are never assumed from personality; they are refined from observed
behaviour (the intent, Bloom level, and outcome of real interactions). Each
observation nudges a dimension via a damped update on the LearnerPreference
entity, so no single interaction overwrites the inferred state and confidence
only grows with accumulated evidence.
"""
from uuid import UUID

import structlog

from src.domain.entities.question import PREFERENCE_DIMENSIONS, LearnerPreference
from src.domain.repositories.question_repository import AbstractLearnerPreferenceRepository

logger = structlog.get_logger(__name__)

# Which dimensions a given interaction is (weak) evidence for, and how strongly.
# Values are the "target" strength (0..1) the observation pulls that dimension toward.
_INTENT_SIGNALS: dict[str, dict[str, float]] = {
    "problem_solving": {"worked_examples": 0.9, "step_by_step": 0.9},
    "test_prep": {"worked_examples": 0.8, "short": 0.7},
    "clarification": {"step_by_step": 0.8, "short": 0.7, "detailed": 0.3},
    "recall": {"short": 0.8},
    "concept_explanation": {"detailed": 0.8, "visual": 0.6},
    "correction_request": {"step_by_step": 0.7},
}

# Higher Bloom engagement is evidence the learner tolerates detailed material.
_HIGH_BLOOM = {"Analyze", "Evaluate", "Create"}


class PreferenceInferenceEngine:
    def __init__(self, preference_repo: AbstractLearnerPreferenceRepository) -> None:
        self._prefs = preference_repo

    async def observe(
        self, user_id: UUID, dimension: str, signal_strength: float
    ) -> LearnerPreference | None:
        if dimension not in PREFERENCE_DIMENSIONS:
            return None
        pref = await self._prefs.get_or_create(user_id, dimension)
        pref.observe(signal_strength)
        return await self._prefs.update(pref)

    async def infer_from_interaction(
        self,
        user_id: UUID,
        intent: str,
        bloom_level: str = "Understand",
        had_misconception: bool = False,
    ) -> list[LearnerPreference]:
        """Fold one real interaction into the preference model. Fail-open per dimension."""
        targets = dict(_INTENT_SIGNALS.get(intent, {}))

        if bloom_level in _HIGH_BLOOM:
            targets["detailed"] = max(targets.get("detailed", 0.0), 0.7)
        # Repeated confusion is evidence the learner needs smaller, guided steps.
        if had_misconception:
            targets["step_by_step"] = max(targets.get("step_by_step", 0.0), 0.8)
            targets["short"] = max(targets.get("short", 0.0), 0.6)

        updated: list[LearnerPreference] = []
        for dimension, strength in targets.items():
            try:
                pref = await self.observe(user_id, dimension, strength)
                if pref:
                    updated.append(pref)
            except Exception as exc:
                logger.warning("preference_observe_failed", dimension=dimension, error=str(exc))
        return updated

    async def get_preferences(self, user_id: UUID) -> list[LearnerPreference]:
        return await self._prefs.list_by_user(user_id)

    async def reliable_preferences(self, user_id: UUID) -> list[LearnerPreference]:
        prefs = await self._prefs.list_by_user(user_id)
        reliable = [p for p in prefs if p.is_reliable]
        reliable.sort(key=lambda p: p.strength, reverse=True)
        return reliable
