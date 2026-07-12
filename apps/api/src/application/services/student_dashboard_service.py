"""
Student home dashboard — upcoming deadlines, recent announcements, submission
progress, performance, bookmarks, and continue-learning. All derived per
request from enrolled classrooms; nothing is stored.
"""
from datetime import UTC, datetime
from uuid import UUID

import structlog

from src.domain.repositories.classroom_repository import AbstractEnrollmentRepository
from src.domain.repositories.lms_repository import (
    AbstractBookmarkRepository,
    AbstractCourseworkRepository,
    AbstractMaterialRepository,
    AbstractMaterialViewRepository,
    AbstractSubmissionRepository,
)

logger = structlog.get_logger(__name__)

_GRADEABLE_TYPES = {"assignment", "homework", "quiz", "exam", "practice_set"}
_MAX_PER_CLASSROOM = 50


class StudentDashboardService:
    def __init__(
        self,
        enrollment_repo: AbstractEnrollmentRepository,
        coursework_repo: AbstractCourseworkRepository,
        submission_repo: AbstractSubmissionRepository,
        bookmark_repo: AbstractBookmarkRepository,
        view_repo: AbstractMaterialViewRepository,
        material_repo: AbstractMaterialRepository,
    ) -> None:
        self._enrollments = enrollment_repo
        self._coursework = coursework_repo
        self._submissions = submission_repo
        self._bookmarks = bookmark_repo
        self._views = view_repo
        self._materials = material_repo

    async def dashboard(self, student_id: UUID) -> dict:
        classrooms = await self._enrollments.list_classrooms_for_student(student_id)
        now = datetime.now(UTC)

        deadlines: list[dict] = []
        announcements: list[dict] = []
        total_assigned = total_submitted = 0
        scores: list[tuple[float, float | None]] = []

        for classroom in classrooms:
            published, _ = await self._coursework.list_by_classroom(
                classroom.id, status="published", page=1, limit=_MAX_PER_CLASSROOM
            )
            for cw in published:
                if cw.type == "announcement":
                    announcements.append(
                        {
                            "id": str(cw.id),
                            "classroom_id": str(classroom.id),
                            "classroom_name": classroom.name,
                            "title": cw.title,
                            "body": (cw.body or "")[:300],
                            "published_at": cw.published_at.isoformat()
                            if cw.published_at
                            else None,
                        }
                    )
                    continue
                if cw.type not in _GRADEABLE_TYPES:
                    continue
                total_assigned += 1
                submission = await self._submissions.get_for_student(cw.id, student_id)
                submitted = bool(submission and submission.status in ("submitted", "returned"))
                if submitted:
                    total_submitted += 1
                    grade = await self._submissions.latest_grade(submission.id)
                    if grade:
                        scores.append((grade.score, grade.max_marks))
                if cw.due_at and cw.due_at > now and not submitted:
                    deadlines.append(
                        {
                            "coursework_id": str(cw.id),
                            "classroom_id": str(classroom.id),
                            "classroom_name": classroom.name,
                            "title": cw.title,
                            "type": cw.type,
                            "due_at": cw.due_at.isoformat(),
                            "max_marks": cw.max_marks,
                        }
                    )

        deadlines.sort(key=lambda d: d["due_at"])
        announcements.sort(key=lambda a: a["published_at"] or "", reverse=True)

        percents = [
            score / max_marks * 100 for score, max_marks in scores if max_marks
        ]
        return {
            "classroom_count": len(classrooms),
            "upcoming_deadlines": deadlines[:10],
            "recent_announcements": announcements[:10],
            "progress": {
                "assigned": total_assigned,
                "submitted": total_submitted,
                "completion_pct": round(total_submitted / total_assigned * 100, 1)
                if total_assigned
                else None,
            },
            "performance": {
                "graded_count": len(scores),
                "average_pct": round(sum(percents) / len(percents), 1) if percents else None,
            },
            "bookmarks": await self._bookmark_summaries(student_id),
            "continue_learning": await self._continue_summaries(student_id),
        }

    async def _bookmark_summaries(self, student_id: UUID) -> list[dict]:
        out: list[dict] = []
        for material_id in (await self._bookmarks.list_material_ids(student_id))[:10]:
            material = await self._materials.get_by_id(material_id)
            if material and not material.is_deleted:
                out.append(
                    {
                        "material_id": str(material.id),
                        "classroom_id": str(material.classroom_id),
                        "title": material.title,
                        "category": material.category,
                    }
                )
        return out

    async def _continue_summaries(self, student_id: UUID) -> list[dict]:
        out: list[dict] = []
        for view in await self._views.list_in_progress(student_id, limit=10):
            material = await self._materials.get_by_id(view.material_id)
            if material and not material.is_deleted:
                out.append(
                    {
                        "material_id": str(material.id),
                        "classroom_id": str(material.classroom_id),
                        "title": material.title,
                        "progress": view.progress,
                        "last_viewed_at": view.last_viewed_at.isoformat(),
                    }
                )
        return out
