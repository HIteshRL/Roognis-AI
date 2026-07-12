"""
Teacher classroom dashboard — derived on every request, never stored
(same principle as the skill profile).
"""
from datetime import UTC, datetime, timedelta
from uuid import UUID

import structlog

from src.domain.exceptions import AuthorizationError, EntityNotFound
from src.domain.repositories.classroom_repository import (
    AbstractClassroomRepository,
    AbstractEnrollmentRepository,
)
from src.domain.repositories.lms_repository import (
    AbstractClassroomTeacherRepository,
    AbstractLmsAnalyticsRepository,
)

logger = structlog.get_logger(__name__)

_INACTIVE_AFTER_DAYS = 7


class TeacherAnalyticsService:
    def __init__(
        self,
        analytics_repo: AbstractLmsAnalyticsRepository,
        classroom_repo: AbstractClassroomRepository,
        enrollment_repo: AbstractEnrollmentRepository,
        teacher_repo: AbstractClassroomTeacherRepository,
    ) -> None:
        self._analytics = analytics_repo
        self._classrooms = classroom_repo
        self._enrollments = enrollment_repo
        self._teachers = teacher_repo

    async def dashboard(self, teacher_id: UUID, classroom_id: UUID) -> dict:
        await self._assert_teaches(teacher_id, classroom_id)

        enrolled = await self._classrooms.count_students(classroom_id)
        coursework_stats = await self._analytics.coursework_stats(classroom_id)
        since = datetime.now(UTC) - timedelta(days=_INACTIVE_AFTER_DAYS)
        inactive = await self._analytics.inactive_students(classroom_id, since)
        recently_active = await self._analytics.recently_active_students(classroom_id)
        material_usage = await self._analytics.material_usage(classroom_id)

        total_expected = enrolled * len(coursework_stats) if coursework_stats else 0
        total_submitted = sum(s["submitted"] for s in coursework_stats)
        completion_rate = (
            round(total_submitted / total_expected * 100, 1) if total_expected else None
        )
        scores = [s["average_score"] for s in coursework_stats if s["average_score"] is not None]
        overall_average = round(sum(scores) / len(scores), 2) if scores else None
        engagement_rate = (
            round((enrolled - len(inactive)) / enrolled * 100, 1) if enrolled else None
        )

        return {
            "students_enrolled": enrolled,
            "assignment_count": len(coursework_stats),
            "completion_rate_pct": completion_rate,
            "overall_average_score": overall_average,
            "engagement_rate_pct": engagement_rate,
            "coursework": coursework_stats,
            "inactive_students": [
                {"id": str(u.id), "username": u.username, "email": u.email} for u in inactive
            ],
            "recently_active_students": [
                {"id": str(u.id), "username": u.username, "email": u.email}
                for u in recently_active
            ],
            "material_usage": material_usage,
        }

    async def _assert_teaches(self, teacher_id: UUID, classroom_id: UUID) -> None:
        classroom = await self._classrooms.get_by_id(classroom_id)
        if not classroom or classroom.is_deleted:
            raise EntityNotFound("Classroom not found")
        if classroom.teacher_id == teacher_id:
            return
        if await self._teachers.get(classroom_id, teacher_id):
            return
        raise AuthorizationError("You do not teach this classroom")
