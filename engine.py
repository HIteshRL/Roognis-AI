"""
Learning Velocity Engine — Roognis AI (Phase 0.4)

Computes two temporal signals:
  1. velocity  — Bloom-weighted mastery points earned per day over a trailing window
  2. retention risks — concepts not reinforced recently, scored via an
     Ebbinghaus-style forgetting curve

Both surface in the student dashboard and are stored on the student profile.
"""
import math
from datetime import UTC, datetime, timedelta
from uuid import UUID

import structlog

from domain import (
    BLOOM_GAINS,
    AbstractLearningSessionRepository,
    AbstractMasteryRepository,
)

logger = structlog.get_logger(__name__)

_VELOCITY_WINDOW_DAYS = 7
_MISCONCEPTION_PENALTY = 5
_RETENTION_DECAY_DAYS = 14
_RETENTION_RISK_THRESHOLD = 0.4
_MAX_AT_RISK = 10


class RetentionRisk:
    def __init__(self, concept_id: UUID, concept_name: str, score: float,
                 days_since_reinforced: int, risk: float) -> None:
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
        since = datetime.now(UTC) - timedelta(days=window_days)
        sessions = await self._sessions.list_since(user_id, since)
        total = sum(
            max(0.0, BLOOM_GAINS.get(s.bloom_level, 5) - (_MISCONCEPTION_PENALTY if s.misconceptions else 0))
            for s in sessions
        )
        velocity = round(total / window_days, 2)
        logger.debug("velocity_computed", user_id=str(user_id), velocity=velocity, sessions=len(sessions))
        return velocity

    async def compute_retention_risks(self, user_id: UUID) -> list[RetentionRisk]:
        records = await self._mastery.list_by_user(user_id)
        now = datetime.now(UTC)
        risks: list[RetentionRisk] = []
        for r in records:
            if r.score < 30:
                continue
            days_since = (now - r.last_updated).days
            strength = r.score / 100
            decay_rate = _RETENTION_DECAY_DAYS * (0.5 + strength)
            risk = round(min(1.0, max(0.0, 1 - math.exp(-days_since / decay_rate))), 3)
            if risk >= _RETENTION_RISK_THRESHOLD:
                risks.append(RetentionRisk(r.concept_id, r.concept_name, r.score, days_since, risk))
        risks.sort(key=lambda x: -x.risk)
        return risks[:_MAX_AT_RISK]
