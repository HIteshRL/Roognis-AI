"""
RecallScheduler — spaced-repetition orchestration over RecallSchedule entities.

Wraps the SM-2 logic that lives on the RecallSchedule entity with persistence and
querying: record a review outcome, list what's due now, and surface concepts whose
predicted retention has decayed below a threshold (candidates for a
``verify_retention`` question).
"""
from datetime import UTC, datetime
from uuid import UUID

import structlog

from src.domain.entities.question import RecallSchedule
from src.domain.repositories.question_repository import AbstractRecallScheduleRepository

logger = structlog.get_logger(__name__)

# Map an evidence signal to an SM-2 recall quality (0..5).
_SIGNAL_QUALITY = {
    "correct": 5,
    "recall_success": 5,
    "partial": 3,
    "preference_signal": 3,
    "incorrect": 1,
    "recall_fail": 1,
    "misconception": 0,
    "skipped": 2,
    "unknown": 3,
}


def quality_from_signal(signal: str) -> int:
    return _SIGNAL_QUALITY.get(signal, 3)


class RecallScheduler:
    def __init__(self, schedule_repo: AbstractRecallScheduleRepository) -> None:
        self._schedules = schedule_repo

    async def record_review(
        self,
        user_id: UUID,
        concept_id: UUID,
        concept_name: str,
        quality: int,
        now: datetime | None = None,
    ) -> RecallSchedule:
        now = now or datetime.now(UTC)
        schedule = await self._schedules.get_or_create(user_id, concept_id, concept_name)
        schedule.review(quality, now=now)
        return await self._schedules.update(schedule)

    async def record_signal(
        self,
        user_id: UUID,
        concept_id: UUID,
        concept_name: str,
        signal: str,
        now: datetime | None = None,
    ) -> RecallSchedule:
        return await self.record_review(
            user_id, concept_id, concept_name, quality_from_signal(signal), now=now
        )

    async def due(self, user_id: UUID, now: datetime | None = None) -> list[RecallSchedule]:
        now = now or datetime.now(UTC)
        return await self._schedules.list_due(user_id, now)

    async def at_risk(
        self, user_id: UUID, threshold: float = 0.6, now: datetime | None = None
    ) -> list[tuple[RecallSchedule, float]]:
        """Concepts whose predicted retention has dropped below ``threshold``."""
        now = now or datetime.now(UTC)
        schedules = await self._schedules.list_by_user(user_id)
        risky = [
            (s, s.retention_at(now))
            for s in schedules
            if s.last_reviewed is not None and s.retention_at(now) < threshold
        ]
        risky.sort(key=lambda pair: pair[1])
        return risky

    async def all(self, user_id: UUID) -> list[RecallSchedule]:
        return await self._schedules.list_by_user(user_id)
