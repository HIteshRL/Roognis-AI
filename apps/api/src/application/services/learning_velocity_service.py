"""
Temporal learning metrics — Phase 0.4 fix.

Replaces the previously-static `learning_velocity` field with a real trend
computed from recent session activity, and adds a retention-risk signal
(Ebbinghaus-style forgetting curve) so stale-but-mastered concepts surface
before they decay out of memory.
"""
import math
from datetime import UTC, datetime, timedelta
from uuid import UUID

import structlog

from src.domain.entities.learning import BLOOM_GAINS
from src.domain.repositories.learning_repository import (
    AbstractLearningSessionRepository,
    AbstractMasteryRepository,
)

logger = structlog.get_logger(__name__)

_VELOCITY_WINDOW_DAYS = 7
_MISCONCEPTION_PENALTY = 5
_RETENTION_DECAY_DAYS = 14   # base half-life-ish constant for the decay curve
_RETENTION_RISK_THRESHOLD = 0.4
_MAX_AT_RISK = 10


class RetentionRisk:
    def __init__(self, concept_id: UUID, concept_name: str, score: float, days_since_reinforced: int, risk: float) -> None:
        self.concept_id = concept_id
        self.concept_name = concept_name
        self.score = score
        self.days_since_reinforced = days_since_reinforced
        self.risk = risk


class LearningVelocityService:
    def __init__(
        self,
        session_repo: AbstractLearningSessionRepository,
        mastery_repo: AbstractMasteryRepository,
    ) -> None:
        self._sessions = session_repo
        self._mastery = mastery_repo

    async def compute_velocity(self, user_id: UUID, window_days: int = _VELOCITY_WINDOW_DAYS) -> float:
        """Points learned per day over the trailing window, from session-level Bloom gains."""
        since = datetime.now(UTC) - timedelta(days=window_days)
        sessions = await self._sessions.list_since(user_id, since)

        total = 0.0
        for s in sessions:
            gain = BLOOM_GAINS.get(s.bloom_level, 5)
            penalty = _MISCONCEPTION_PENALTY if s.misconceptions else 0
            total += max(0.0, gain - penalty)

        velocity = round(total / window_days, 2)
        logger.debug("velocity_computed", user_id=str(user_id), velocity=velocity, sessions=len(sessions))
        return velocity

    async def compute_retention_risks(self, user_id: UUID) -> list[RetentionRisk]:
        """
        Flags mastered/developing concepts that haven't been reinforced recently.
        Stronger mastery decays slower; risk climbs the longer a concept goes untouched.
        """
        records = await self._mastery.list_by_user(user_id)
        now = datetime.now(UTC)

        risks: list[RetentionRisk] = []
        for r in records:
            if r.score < 30:
                continue  # not_started/emerging — no retention concept applies yet

            days_since = (now - r.last_updated).days
            strength = r.score / 100
            decay_rate = _RETENTION_DECAY_DAYS * (0.5 + strength)
            risk = 1 - math.exp(-days_since / decay_rate)
            risk = round(min(1.0, max(0.0, risk)), 3)

            if risk >= _RETENTION_RISK_THRESHOLD:
                risks.append(
                    RetentionRisk(
                        concept_id=r.concept_id,
                        concept_name=r.concept_name,
                        score=r.score,
                        days_since_reinforced=days_since,
                        risk=risk,
                    )
                )

        risks.sort(key=lambda x: -x.risk)
        return risks[:_MAX_AT_RISK]
