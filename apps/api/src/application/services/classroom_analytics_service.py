"""
ClassroomAnalyticsService — the Teacher Dashboard read model.

Composes a classroom roster with per-student learning aggregates and class-wide
rollups. Auth is delegated to ClassroomService.roster(), which enforces
_assert_can_manage (classroom teacher or school admin only). All learning data
is fetched with batch GROUP BY queries — no per-student N+1.
"""
from uuid import UUID

from src.application.dtos.school import (
    ClassroomAnalyticsResponse,
    MasteryBucket,
    MisconceptionConcept,
    StudentAnalyticsEntry,
)
from src.application.services.classroom_service import ClassroomService
from src.domain.repositories.learning_repository import (
    AbstractLearningGapRepository,
    AbstractLearningSessionRepository,
    AbstractMasteryRepository,
)

# Mastery buckets share the thresholds baked into MasteryRecord.label.
_BUCKET_ORDER = ["struggling", "developing", "proficient", "mastered", "no_data"]


def _bucket(score: float) -> str:
    if score < 30:
        return "struggling"
    if score < 60:
        return "developing"
    if score < 85:
        return "proficient"
    return "mastered"


class ClassroomAnalyticsService:
    def __init__(
        self,
        classroom_service: ClassroomService,
        mastery_repo: AbstractMasteryRepository,
        gap_repo: AbstractLearningGapRepository,
        session_repo: AbstractLearningSessionRepository,
    ) -> None:
        self._classrooms = classroom_service
        self._mastery = mastery_repo
        self._gaps = gap_repo
        self._sessions = session_repo

    async def classroom_analytics(
        self, classroom_id: UUID, user_id: UUID
    ) -> ClassroomAnalyticsResponse:
        # Enforces manage-auth + returns (enrollment, username, email) rows.
        roster = [
            (e, name, email)
            for (e, name, email) in await self._classrooms.roster(classroom_id, user_id)
            if e.is_active
        ]
        ids = [e.student_id for (e, _, _) in roster]

        if not ids:
            return ClassroomAnalyticsResponse(
                classroom_id=str(classroom_id),
                student_count=0,
                total_sessions=0,
                class_avg_mastery=0.0,
                mastery_distribution=[MasteryBucket(label=b, count=0) for b in _BUCKET_ORDER],
                top_misconceptions=[],
                students=[],
            )

        avg_by = await self._mastery.average_scores_by_users(ids)
        gaps_by = await self._gaps.active_gap_counts_by_users(ids)
        stats_by = await self._sessions.session_stats_by_users(ids)
        top = await self._gaps.top_concepts_by_users(ids, limit=5)

        students = []
        buckets = dict.fromkeys(_BUCKET_ORDER, 0)
        for enrollment, username, email in roster:
            sid = enrollment.student_id
            count, last = stats_by.get(sid, (0, None))
            score = avg_by.get(sid)
            buckets["no_data" if score is None else _bucket(score)] += 1
            students.append(
                StudentAnalyticsEntry(
                    student_id=str(sid),
                    username=username,
                    email=email,
                    avg_mastery=score if score is not None else 0.0,
                    active_gap_count=gaps_by.get(sid, 0),
                    session_count=count,
                    last_activity=last.isoformat() if last else None,
                )
            )

        scored = [avg_by[sid] for sid in ids if sid in avg_by]
        class_avg = round(sum(scored) / len(scored), 2) if scored else 0.0
        total_sessions = sum(count for count, _ in stats_by.values())

        return ClassroomAnalyticsResponse(
            classroom_id=str(classroom_id),
            student_count=len(ids),
            total_sessions=total_sessions,
            class_avg_mastery=class_avg,
            mastery_distribution=[MasteryBucket(label=b, count=buckets[b]) for b in _BUCKET_ORDER],
            top_misconceptions=[
                MisconceptionConcept(concept_name=name, student_count=n) for name, n in top
            ],
            students=students,
        )
