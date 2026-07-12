"""
Coursework lifecycle — announcements, assignments, homework, quizzes, exams,
practice sets, discussion threads, and polls.

Lifecycle: draft → (scheduled) → published → archived. Duplicate produces a
fresh draft. Updates take an optional expected_version for optimistic locking.
Scheduled items auto-publish lazily: any read that encounters a scheduled item
whose time has passed flips it to published (no background worker needed).
"""
from datetime import UTC, datetime
from uuid import UUID

import structlog

from src.application.dtos.coursework import (
    AddAttachmentRequest,
    CourseworkAttachmentResponse,
    CourseworkListResponse,
    CourseworkResponse,
    CreateCourseworkRequest,
    UpdateCourseworkRequest,
)
from src.domain.entities.lms import (
    Coursework,
    CourseworkAttachment,
    PollVote,
)
from src.domain.exceptions import AuthorizationError, EntityNotFound, ValidationError
from src.domain.repositories.classroom_repository import (
    AbstractClassroomRepository,
    AbstractEnrollmentRepository,
)
from src.domain.repositories.lms_repository import (
    AbstractClassroomTeacherRepository,
    AbstractCourseworkRepository,
    AbstractSubmissionRepository,
)

logger = structlog.get_logger(__name__)

_GRADEABLE_TYPES = {"assignment", "homework", "quiz", "exam", "practice_set"}


class CourseworkService:
    def __init__(
        self,
        coursework_repo: AbstractCourseworkRepository,
        classroom_repo: AbstractClassroomRepository,
        enrollment_repo: AbstractEnrollmentRepository,
        teacher_repo: AbstractClassroomTeacherRepository,
        submission_repo: AbstractSubmissionRepository | None = None,
        notification_svc=None,
    ) -> None:
        self._coursework = coursework_repo
        self._classrooms = classroom_repo
        self._enrollments = enrollment_repo
        self._teachers = teacher_repo
        self._submissions = submission_repo
        self._notify = notification_svc

    # ── Create / update / lifecycle (teacher) ────────────────────────────────

    async def create(
        self, teacher_id: UUID, classroom_id: UUID, dto: CreateCourseworkRequest
    ) -> CourseworkResponse:
        classroom = await self._assert_teaches(teacher_id, classroom_id)
        if dto.type == "poll" and not dto.poll_options:
            raise ValidationError("A poll needs at least two options")
        if dto.poll_options is not None and len(dto.poll_options) < 2:
            raise ValidationError("A poll needs at least two options")

        coursework = Coursework(
            classroom_id=classroom_id,
            author_id=teacher_id,
            type=dto.type,
            title=dto.title,
            body=dto.body,
            due_at=dto.due_at,
            allow_late=dto.allow_late,
            max_marks=dto.max_marks,
            rubric=[r.model_dump() for r in dto.rubric] if dto.rubric else None,
            questions=dto.questions,
            poll_options=dto.poll_options,
            settings=dto.settings or {},
        )
        if dto.publish:
            coursework.publish()
        elif dto.scheduled_at:
            coursework.status = "scheduled"
            coursework.scheduled_at = dto.scheduled_at

        coursework = await self._coursework.create(coursework)
        if coursework.status == "published":
            await self._announce(classroom.name, coursework)
        logger.info(
            "coursework_created",
            coursework_id=str(coursework.id),
            type=coursework.type,
            status=coursework.status,
        )
        return await self._to_response(coursework)

    async def update(
        self, teacher_id: UUID, coursework_id: UUID, dto: UpdateCourseworkRequest
    ) -> CourseworkResponse:
        coursework = await self._get(coursework_id)
        await self._assert_teaches(teacher_id, coursework.classroom_id)
        for field_name in (
            "title", "body", "due_at", "allow_late", "max_marks",
            "questions", "poll_options", "settings",
        ):
            value = getattr(dto, field_name)
            if value is not None:
                setattr(coursework, field_name, value)
        if dto.rubric is not None:
            coursework.rubric = [r.model_dump() for r in dto.rubric]
        coursework = await self._coursework.update(
            coursework, expected_version=dto.expected_version
        )
        return await self._to_response(coursework)

    async def publish(self, teacher_id: UUID, coursework_id: UUID) -> CourseworkResponse:
        coursework = await self._get(coursework_id)
        classroom = await self._assert_teaches(teacher_id, coursework.classroom_id)
        if coursework.status == "published":
            return await self._to_response(coursework)
        coursework.publish()
        coursework = await self._coursework.update(coursework)
        await self._announce(classroom.name, coursework)
        return await self._to_response(coursework)

    async def schedule(
        self, teacher_id: UUID, coursework_id: UUID, scheduled_at: datetime
    ) -> CourseworkResponse:
        coursework = await self._get(coursework_id)
        await self._assert_teaches(teacher_id, coursework.classroom_id)
        if coursework.status == "published":
            raise ValidationError("Already published")
        coursework.status = "scheduled"
        coursework.scheduled_at = scheduled_at
        coursework = await self._coursework.update(coursework)
        return await self._to_response(coursework)

    async def archive(self, teacher_id: UUID, coursework_id: UUID) -> CourseworkResponse:
        coursework = await self._get(coursework_id)
        await self._assert_teaches(teacher_id, coursework.classroom_id)
        coursework.status = "archived"
        coursework = await self._coursework.update(coursework)
        return await self._to_response(coursework)

    async def duplicate(self, teacher_id: UUID, coursework_id: UUID) -> CourseworkResponse:
        original = await self._get(coursework_id)
        await self._assert_teaches(teacher_id, original.classroom_id)
        copy = Coursework(
            classroom_id=original.classroom_id,
            author_id=teacher_id,
            type=original.type,
            title=f"{original.title} (copy)",
            body=original.body,
            due_at=original.due_at,
            allow_late=original.allow_late,
            max_marks=original.max_marks,
            rubric=original.rubric,
            questions=original.questions,
            poll_options=original.poll_options,
            settings=dict(original.settings),
        )
        copy = await self._coursework.create(copy)
        for attachment in await self._coursework.list_attachments(coursework_id):
            await self._coursework.add_attachment(
                CourseworkAttachment(
                    coursework_id=copy.id,
                    material_id=attachment.material_id,
                    link_url=attachment.link_url,
                    title=attachment.title,
                )
            )
        return await self._to_response(copy)

    async def delete(self, teacher_id: UUID, coursework_id: UUID) -> None:
        coursework = await self._get(coursework_id)
        await self._assert_teaches(teacher_id, coursework.classroom_id)
        coursework.is_deleted = True
        coursework.deleted_at = datetime.now(UTC)
        await self._coursework.update(coursework)

    # ── Attachments ──────────────────────────────────────────────────────────

    async def add_attachment(
        self, teacher_id: UUID, coursework_id: UUID, dto: AddAttachmentRequest
    ) -> CourseworkAttachmentResponse:
        coursework = await self._get(coursework_id)
        await self._assert_teaches(teacher_id, coursework.classroom_id)
        if not dto.material_id and not dto.link_url:
            raise ValidationError("Attachment needs a material_id or a link_url")
        attachment = await self._coursework.add_attachment(
            CourseworkAttachment(
                coursework_id=coursework_id,
                material_id=UUID(dto.material_id) if dto.material_id else None,
                link_url=dto.link_url,
                title=dto.title,
            )
        )
        return self._attachment_to_response(attachment)

    async def remove_attachment(
        self, teacher_id: UUID, coursework_id: UUID, attachment_id: UUID
    ) -> None:
        coursework = await self._get(coursework_id)
        await self._assert_teaches(teacher_id, coursework.classroom_id)
        await self._coursework.delete_attachment(attachment_id)

    # ── Listing ──────────────────────────────────────────────────────────────

    async def list_for_teacher(
        self,
        teacher_id: UUID,
        classroom_id: UUID,
        type: str | None = None,
        status: str | None = None,
        search: str | None = None,
        page: int = 1,
        limit: int = 50,
    ) -> CourseworkListResponse:
        await self._assert_teaches(teacher_id, classroom_id)
        await self._auto_publish_due(classroom_id)
        items, total = await self._coursework.list_by_classroom(
            classroom_id, type=type, status=status, search=search, page=page, limit=limit
        )
        responses = [await self._to_response(c, with_stats=True) for c in items]
        return CourseworkListResponse(items=responses, total=total, page=page, limit=limit)

    async def list_for_student(
        self,
        student_id: UUID,
        classroom_id: UUID,
        type: str | None = None,
        search: str | None = None,
        page: int = 1,
        limit: int = 50,
    ) -> CourseworkListResponse:
        await self._assert_enrolled(student_id, classroom_id)
        await self._auto_publish_due(classroom_id)
        items, total = await self._coursework.list_by_classroom(
            classroom_id, type=type, status="published", search=search, page=page, limit=limit
        )
        responses = [
            await self._to_response(c, for_student=student_id) for c in items
        ]
        return CourseworkListResponse(items=responses, total=total, page=page, limit=limit)

    async def get_for_user(
        self, user_id: UUID, coursework_id: UUID, as_teacher: bool
    ) -> CourseworkResponse:
        coursework = await self._get(coursework_id)
        if as_teacher:
            await self._assert_teaches(user_id, coursework.classroom_id)
            return await self._to_response(coursework, with_stats=True)
        await self._assert_enrolled(user_id, coursework.classroom_id)
        if not coursework.is_visible_to_students:
            raise EntityNotFound("Coursework not found")
        return await self._to_response(coursework, for_student=user_id)

    # ── Polls ────────────────────────────────────────────────────────────────

    async def vote(
        self, student_id: UUID, coursework_id: UUID, option_index: int
    ) -> dict[int, int]:
        coursework = await self._get(coursework_id)
        await self._assert_enrolled(student_id, coursework.classroom_id)
        if coursework.type != "poll" or not coursework.is_visible_to_students:
            raise ValidationError("This item is not an open poll")
        options = coursework.poll_options or []
        if option_index >= len(options):
            raise ValidationError("Invalid poll option")
        await self._coursework.upsert_poll_vote(
            PollVote(coursework_id=coursework_id, user_id=student_id, option_index=option_index)
        )
        return await self._coursework.poll_results(coursework_id)

    # ── Helpers ──────────────────────────────────────────────────────────────

    async def _auto_publish_due(self, classroom_id: UUID) -> None:
        """Lazily flip scheduled items whose time has passed. Fail-open."""
        try:
            for coursework in await self._coursework.list_scheduled_due(datetime.now(UTC)):
                if coursework.classroom_id != classroom_id:
                    continue
                coursework.publish()
                await self._coursework.update(coursework)
                classroom = await self._classrooms.get_by_id(classroom_id)
                if classroom:
                    await self._announce(classroom.name, coursework)
        except Exception as exc:
            logger.warning("auto_publish_failed", error=str(exc))

    async def _announce(self, classroom_name: str, coursework: Coursework) -> None:
        if not self._notify:
            return
        students = await self._enrollments.list_students(coursework.classroom_id)
        label = coursework.type.replace("_", " ").title()
        await self._notify.emit_many(
            [s.id for s in students],
            type=f"new_{coursework.type}",
            title=f"{label} in {classroom_name}: {coursework.title}",
            body=(coursework.body or "")[:200],
            data={
                "classroom_id": str(coursework.classroom_id),
                "coursework_id": str(coursework.id),
                "due_at": coursework.due_at.isoformat() if coursework.due_at else None,
            },
        )

    async def _assert_teaches(self, teacher_id: UUID, classroom_id: UUID):
        classroom = await self._classrooms.get_by_id(classroom_id)
        if not classroom or classroom.is_deleted:
            raise EntityNotFound("Classroom not found")
        if classroom.teacher_id == teacher_id:
            return classroom
        if await self._teachers.get(classroom_id, teacher_id):
            return classroom
        raise AuthorizationError("You do not teach this classroom")

    async def _assert_enrolled(self, student_id: UUID, classroom_id: UUID) -> None:
        if not await self._enrollments.is_enrolled(classroom_id, student_id):
            raise AuthorizationError("You are not enrolled in this class")

    async def _get(self, coursework_id: UUID) -> Coursework:
        coursework = await self._coursework.get_by_id(coursework_id)
        if not coursework or coursework.is_deleted:
            raise EntityNotFound("Coursework not found")
        return coursework

    async def _to_response(
        self,
        c: Coursework,
        with_stats: bool = False,
        for_student: UUID | None = None,
    ) -> CourseworkResponse:
        attachments = [
            self._attachment_to_response(a)
            for a in await self._coursework.list_attachments(c.id)
        ]
        submission_count = graded_count = None
        my_status = None
        poll_results = my_vote = None

        if with_stats and self._submissions and c.type in _GRADEABLE_TYPES:
            counts = await self._submissions.count_by_status(c.id)
            submission_count = counts.get("submitted", 0) + counts.get("returned", 0)
            graded_count = counts.get("returned", 0)
        if for_student and self._submissions and c.type in _GRADEABLE_TYPES:
            submission = await self._submissions.get_for_student(c.id, for_student)
            my_status = submission.status if submission else None
        if c.type == "poll":
            poll_results = await self._coursework.poll_results(c.id)
            if for_student:
                vote = await self._coursework.get_poll_vote(c.id, for_student)
                my_vote = vote.option_index if vote else None

        return CourseworkResponse(
            id=str(c.id),
            classroom_id=str(c.classroom_id),
            author_id=str(c.author_id),
            type=c.type,
            title=c.title,
            body=c.body,
            status=c.status,
            scheduled_at=c.scheduled_at.isoformat() if c.scheduled_at else None,
            published_at=c.published_at.isoformat() if c.published_at else None,
            due_at=c.due_at.isoformat() if c.due_at else None,
            allow_late=c.allow_late,
            max_marks=c.max_marks,
            rubric=c.rubric,
            questions=c.questions,
            poll_options=c.poll_options,
            settings=c.settings,
            version=c.version,
            attachments=attachments,
            submission_count=submission_count,
            graded_count=graded_count,
            my_submission_status=my_status,
            poll_results=poll_results,
            my_poll_vote=my_vote,
            created_at=c.created_at.isoformat(),
            updated_at=c.updated_at.isoformat(),
        )

    @staticmethod
    def _attachment_to_response(a: CourseworkAttachment) -> CourseworkAttachmentResponse:
        return CourseworkAttachmentResponse(
            id=str(a.id),
            material_id=str(a.material_id) if a.material_id else None,
            link_url=a.link_url,
            title=a.title,
        )
