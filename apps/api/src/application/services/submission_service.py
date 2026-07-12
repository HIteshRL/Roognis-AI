"""
Student submissions and teacher grading.

One submission row per (coursework, student); resubmission bumps `attempt`
and replaces attachments. Grades are append-only — a regrade adds a row and
the latest one wins, so grade history is always auditable.
"""
from datetime import UTC, datetime
from uuid import UUID, uuid4

import structlog

from src.application.dtos.submission import (
    GradeRequest,
    GradeResponse,
    SubmissionAttachmentResponse,
    SubmissionListResponse,
    SubmissionResponse,
)
from src.domain.entities.lms import (
    Coursework,
    Grade,
    Submission,
    SubmissionAttachment,
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
from src.domain.repositories.user_repository import AbstractUserRepository

logger = structlog.get_logger(__name__)

_SUBMITTABLE_TYPES = {"assignment", "homework", "quiz", "exam", "practice_set"}


class SubmissionService:
    def __init__(
        self,
        submission_repo: AbstractSubmissionRepository,
        coursework_repo: AbstractCourseworkRepository,
        classroom_repo: AbstractClassroomRepository,
        enrollment_repo: AbstractEnrollmentRepository,
        teacher_repo: AbstractClassroomTeacherRepository,
        user_repo: AbstractUserRepository,
        storage,  # AbstractFileStorage
        notification_svc=None,
    ) -> None:
        self._submissions = submission_repo
        self._coursework = coursework_repo
        self._classrooms = classroom_repo
        self._enrollments = enrollment_repo
        self._teachers = teacher_repo
        self._users = user_repo
        self._storage = storage
        self._notify = notification_svc

    # ── Student side ─────────────────────────────────────────────────────────

    async def submit(
        self,
        student_id: UUID,
        coursework_id: UUID,
        text_answer: str | None,
        files: list[tuple[str, bytes, str]],  # (filename, bytes, content_type)
    ) -> SubmissionResponse:
        coursework = await self._submittable_coursework(student_id, coursework_id)
        now = datetime.now(UTC)
        if not coursework.accepts_submissions_at(now):
            raise ValidationError("The deadline has passed and late submissions are off")
        if not text_answer and not files:
            raise ValidationError("A submission needs a text answer or at least one file")

        submission = await self._submissions.get_for_student(coursework_id, student_id)
        if submission and submission.is_submitted:
            raise ValidationError("Already submitted — withdraw or resubmit instead")

        if submission:
            submission.text_answer = text_answer
            submission.status = "submitted"
            submission.submitted_at = now
            submission.is_late = coursework.is_late_at(now)
            submission = await self._submissions.update(submission)
            await self._delete_stored(await self._submissions.clear_attachments(submission.id))
        else:
            submission = await self._submissions.create(
                Submission(
                    coursework_id=coursework_id,
                    student_id=student_id,
                    status="submitted",
                    text_answer=text_answer,
                    submitted_at=now,
                    is_late=coursework.is_late_at(now),
                )
            )
        await self._store_files(submission, files)

        student = await self._users.get_by_id(student_id)
        if self._notify and student:
            await self._notify.emit(
                user_id=coursework.author_id,
                type="submission_received",
                title=f"{student.username} submitted '{coursework.title}'",
                data={
                    "coursework_id": str(coursework_id),
                    "submission_id": str(submission.id),
                    "is_late": submission.is_late,
                },
            )
        logger.info("submission_created", submission_id=str(submission.id), late=submission.is_late)
        return await self._to_response(submission, include_private=True)

    async def resubmit(
        self,
        student_id: UUID,
        coursework_id: UUID,
        text_answer: str | None,
        files: list[tuple[str, bytes, str]],
    ) -> SubmissionResponse:
        coursework = await self._submittable_coursework(student_id, coursework_id)
        submission = await self._submissions.get_for_student(coursework_id, student_id)
        if not submission:
            raise EntityNotFound("Nothing submitted yet — use submit")
        now = datetime.now(UTC)
        if not coursework.accepts_submissions_at(now):
            raise ValidationError("The deadline has passed and late submissions are off")
        if not text_answer and not files:
            raise ValidationError("A submission needs a text answer or at least one file")

        submission.text_answer = text_answer
        submission.status = "submitted"
        submission.attempt += 1
        submission.submitted_at = now
        submission.is_late = coursework.is_late_at(now)
        submission = await self._submissions.update(submission)
        await self._delete_stored(await self._submissions.clear_attachments(submission.id))
        await self._store_files(submission, files)
        return await self._to_response(submission, include_private=True)

    async def withdraw(self, student_id: UUID, coursework_id: UUID) -> None:
        coursework = await self._submittable_coursework(student_id, coursework_id)
        submission = await self._submissions.get_for_student(coursework_id, student_id)
        if not submission or not submission.is_submitted:
            raise EntityNotFound("No submitted work to withdraw")
        if coursework.due_at and datetime.now(UTC) > coursework.due_at:
            raise ValidationError("Cannot withdraw after the deadline")
        submission.status = "withdrawn"
        await self._submissions.update(submission)

    async def my_submission(
        self, student_id: UUID, coursework_id: UUID
    ) -> SubmissionResponse | None:
        await self._submittable_coursework(student_id, coursework_id)
        submission = await self._submissions.get_for_student(coursework_id, student_id)
        if not submission:
            return None
        return await self._to_response(submission, include_private=True)

    async def my_grades(
        self, student_id: UUID, classroom_id: UUID, page: int = 1, limit: int = 50
    ) -> SubmissionListResponse:
        if not await self._enrollments.is_enrolled(classroom_id, student_id):
            raise AuthorizationError("You are not enrolled in this class")
        items, total = await self._submissions.list_by_student(
            student_id, classroom_id=classroom_id, page=page, limit=limit
        )
        responses = [await self._to_response(s, include_private=True) for s in items]
        return SubmissionListResponse(items=responses, total=total, page=page, limit=limit)

    # ── Teacher side ─────────────────────────────────────────────────────────

    async def list_for_coursework(
        self,
        teacher_id: UUID,
        coursework_id: UUID,
        status: str | None = None,
        page: int = 1,
        limit: int = 50,
    ) -> SubmissionListResponse:
        coursework = await self._get_coursework(coursework_id)
        await self._assert_teaches(teacher_id, coursework.classroom_id)
        items, total = await self._submissions.list_by_coursework(
            coursework_id, status=status, page=page, limit=limit
        )
        responses = [
            await self._to_response(s, include_private=True, with_student=True) for s in items
        ]
        return SubmissionListResponse(items=responses, total=total, page=page, limit=limit)

    async def download_attachment(
        self, teacher_id: UUID, submission_id: UUID, attachment_id: UUID
    ) -> tuple[SubmissionAttachment, bytes]:
        submission = await self._get_submission(submission_id)
        coursework = await self._get_coursework(submission.coursework_id)
        await self._assert_teaches(teacher_id, coursework.classroom_id)
        for attachment in await self._submissions.list_attachments(submission_id):
            if attachment.id == attachment_id:
                return attachment, await self._storage.read(attachment.storage_path)
        raise EntityNotFound("Attachment not found")

    async def grade(
        self, teacher_id: UUID, submission_id: UUID, dto: GradeRequest
    ) -> SubmissionResponse:
        submission = await self._get_submission(submission_id)
        coursework = await self._get_coursework(submission.coursework_id)
        await self._assert_teaches(teacher_id, coursework.classroom_id)
        if coursework.max_marks is not None and dto.score > coursework.max_marks:
            raise ValidationError(
                f"Score exceeds max marks ({coursework.max_marks})"
            )
        previous = await self._submissions.latest_grade(submission_id)
        await self._submissions.add_grade(
            Grade(
                submission_id=submission_id,
                grader_id=teacher_id,
                score=dto.score,
                max_marks=coursework.max_marks,
                rubric_scores=dto.rubric_scores,
                comment=dto.comment,
                private_feedback=dto.private_feedback,
                is_returned=dto.return_to_student,
                is_regrade=previous is not None,
            )
        )
        if dto.return_to_student:
            submission.status = "returned"
            submission = await self._submissions.update(submission)
            if self._notify:
                await self._notify.emit(
                    user_id=submission.student_id,
                    type="work_graded",
                    title=f"'{coursework.title}' was graded: {dto.score}"
                    + (f"/{coursework.max_marks}" if coursework.max_marks else ""),
                    body=dto.comment or "",
                    data={
                        "coursework_id": str(coursework.id),
                        "submission_id": str(submission_id),
                    },
                )
        logger.info(
            "submission_graded",
            submission_id=str(submission_id),
            regrade=previous is not None,
        )
        return await self._to_response(submission, include_private=True, with_student=True)

    async def return_submission(
        self, teacher_id: UUID, submission_id: UUID
    ) -> SubmissionResponse:
        """Return ungraded work (e.g. asking for changes)."""
        submission = await self._get_submission(submission_id)
        coursework = await self._get_coursework(submission.coursework_id)
        await self._assert_teaches(teacher_id, coursework.classroom_id)
        submission.status = "returned"
        submission = await self._submissions.update(submission)
        if self._notify:
            await self._notify.emit(
                user_id=submission.student_id,
                type="work_returned",
                title=f"'{coursework.title}' was returned to you",
                data={"coursework_id": str(coursework.id)},
            )
        return await self._to_response(submission, include_private=True, with_student=True)

    # ── Helpers ──────────────────────────────────────────────────────────────

    async def _store_files(
        self, submission: Submission, files: list[tuple[str, bytes, str]]
    ) -> None:
        for filename, data, content_type in files:
            safe_name = filename.replace("/", "_").replace("\\", "_")
            path = await self._storage.save(
                data,
                f"lms/submissions/{submission.id}/{uuid4().hex[:8]}_{safe_name}",
            )
            await self._submissions.add_attachment(
                SubmissionAttachment(
                    submission_id=submission.id,
                    filename=filename,
                    file_type=content_type,
                    file_size=len(data),
                    storage_path=path,
                )
            )

    async def _delete_stored(self, attachments: list[SubmissionAttachment]) -> None:
        for attachment in attachments:
            try:
                await self._storage.delete(attachment.storage_path)
            except Exception as exc:
                logger.warning("submission_file_delete_failed", error=str(exc))

    async def _submittable_coursework(
        self, student_id: UUID, coursework_id: UUID
    ) -> Coursework:
        coursework = await self._get_coursework(coursework_id)
        if coursework.type not in _SUBMITTABLE_TYPES:
            raise ValidationError("This item does not accept submissions")
        if not await self._enrollments.is_enrolled(coursework.classroom_id, student_id):
            raise AuthorizationError("You are not enrolled in this class")
        if not coursework.is_visible_to_students:
            raise EntityNotFound("Coursework not found")
        return coursework

    async def _get_coursework(self, coursework_id: UUID) -> Coursework:
        coursework = await self._coursework.get_by_id(coursework_id)
        if not coursework or coursework.is_deleted:
            raise EntityNotFound("Coursework not found")
        return coursework

    async def _get_submission(self, submission_id: UUID) -> Submission:
        submission = await self._submissions.get_by_id(submission_id)
        if not submission:
            raise EntityNotFound("Submission not found")
        return submission

    async def _assert_teaches(self, teacher_id: UUID, classroom_id: UUID) -> None:
        classroom = await self._classrooms.get_by_id(classroom_id)
        if not classroom or classroom.is_deleted:
            raise EntityNotFound("Classroom not found")
        if classroom.teacher_id == teacher_id:
            return
        if await self._teachers.get(classroom_id, teacher_id):
            return
        raise AuthorizationError("You do not teach this classroom")

    async def _to_response(
        self,
        s: Submission,
        include_private: bool = False,
        with_student: bool = False,
    ) -> SubmissionResponse:
        attachments = [
            SubmissionAttachmentResponse(
                id=str(a.id),
                filename=a.filename,
                file_type=a.file_type,
                file_size=a.file_size,
                created_at=a.created_at.isoformat(),
            )
            for a in await self._submissions.list_attachments(s.id)
        ]
        grades = await self._submissions.list_grades(s.id)
        grade_responses = [self._grade_to_response(g, include_private) for g in grades]
        student_name = None
        if with_student:
            student = await self._users.get_by_id(s.student_id)
            student_name = student.username if student else None
        return SubmissionResponse(
            id=str(s.id),
            coursework_id=str(s.coursework_id),
            student_id=str(s.student_id),
            student_name=student_name,
            status=s.status,
            text_answer=s.text_answer,
            attempt=s.attempt,
            is_late=s.is_late,
            submitted_at=s.submitted_at.isoformat() if s.submitted_at else None,
            attachments=attachments,
            grade=grade_responses[0] if grade_responses else None,
            grade_history=grade_responses,
            created_at=s.created_at.isoformat(),
            updated_at=s.updated_at.isoformat(),
        )

    @staticmethod
    def _grade_to_response(g: Grade, include_private: bool) -> GradeResponse:
        return GradeResponse(
            id=str(g.id),
            grader_id=str(g.grader_id) if g.grader_id else None,
            score=g.score,
            max_marks=g.max_marks,
            rubric_scores=g.rubric_scores,
            comment=g.comment,
            private_feedback=g.private_feedback if include_private else None,
            is_returned=g.is_returned,
            is_regrade=g.is_regrade,
            created_at=g.created_at.isoformat(),
        )
