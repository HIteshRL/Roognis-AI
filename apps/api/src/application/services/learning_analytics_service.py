from uuid import UUID

import structlog

from src.application.dtos.learning import LearningAnalyticsResponse, RetentionRiskResponse
from src.application.services.learning_velocity_service import LearningVelocityService
from src.domain.repositories.learning_repository import (
    AbstractLearningGapRepository,
    AbstractLearningSessionRepository,
    AbstractMasteryRepository,
)

logger = structlog.get_logger(__name__)


class LearningAnalyticsService:
    def __init__(
        self,
        session_repo: AbstractLearningSessionRepository,
        mastery_repo: AbstractMasteryRepository,
        gap_repo: AbstractLearningGapRepository,
        velocity_svc: LearningVelocityService | None = None,
    ) -> None:
        self._sessions = session_repo
        self._mastery = mastery_repo
        self._gaps = gap_repo
        self._velocity = velocity_svc

    async def get_analytics(self, user_id: UUID) -> LearningAnalyticsResponse:
        total_sessions = await self._sessions.count_by_user(user_id)
        recent_concepts = await self._sessions.recent_concepts(user_id, days=7)

        mastery_records = await self._mastery.list_by_user(user_id)
        mastered = sum(1 for r in mastery_records if r.label == "mastered")
        developing = sum(1 for r in mastery_records if r.label == "developing")
        emerging = sum(1 for r in mastery_records if r.label == "emerging")
        not_started = sum(1 for r in mastery_records if r.label == "not_started")
        avg_mastery = round(
            sum(r.score for r in mastery_records) / len(mastery_records)
            if mastery_records
            else 0.0,
            2,
        )

        gaps = await self._gaps.list_by_user(user_id, include_resolved=True)
        active_gaps = sum(1 for g in gaps if not g.is_resolved)
        critical_gaps = sum(
            1 for g in gaps if not g.is_resolved and g.severity == "critical"
        )

        # Aggregate bloom levels from last 7 days
        recent_sessions = await self._sessions.list_by_user(user_id, limit=50, offset=0)
        bloom_counts: dict[str, int] = {}
        for s in recent_sessions:
            bloom_counts[s.bloom_level] = bloom_counts.get(s.bloom_level, 0) + 1

        velocity_trend = 0.0
        at_risk: list[RetentionRiskResponse] = []
        if self._velocity:
            velocity_trend = await self._velocity.compute_velocity(user_id)
            risks = await self._velocity.compute_retention_risks(user_id)
            at_risk = [
                RetentionRiskResponse(
                    concept_id=r.concept_id,
                    concept_name=r.concept_name,
                    score=r.score,
                    days_since_reinforced=r.days_since_reinforced,
                    risk=r.risk,
                )
                for r in risks
            ]

        return LearningAnalyticsResponse(
            user_id=user_id,
            total_sessions=total_sessions,
            total_concepts_encountered=len(mastery_records),
            average_mastery=avg_mastery,
            mastered_count=mastered,
            developing_count=developing,
            emerging_count=emerging,
            not_started_count=not_started,
            active_gaps=active_gaps,
            critical_gaps=critical_gaps,
            recent_bloom_levels=bloom_counts,
            recent_concepts=list(dict.fromkeys(recent_concepts))[:10],
            velocity_trend=velocity_trend,
            at_risk_concepts=at_risk,
        )

