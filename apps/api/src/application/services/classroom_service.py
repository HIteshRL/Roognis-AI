import secrets
from uuid import UUID

import structlog

from src.domain.entities.school import Classroom, Enrollment, Role
from src.domain.exceptions import (
    AuthorizationError,
    EntityNotFound,
    ValidationError,
)
from src.domain.repositories.school_repository import (
    AbstractClassroomRepository,
    AbstractEnrollmentRepository,
    AbstractSchoolMemberRepository,
    AbstractSyllabusRepository,
)
from src.domain.repositories.user_repository import AbstractUserRepository

logger = structlog.get_logger(__name__)

_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no ambiguous 0/O/1/I


class ClassroomService:
    def __init__(
        self,
        classroom_repo: AbstractClassroomRepository,
        enrollment_repo: AbstractEnrollmentRepository,
        member_repo: AbstractSchoolMemberRepository,
        syllabus_repo: AbstractSyllabusRepository,
        user_repo: AbstractUserRepository,
        join_code_length: int = 6,
    ) -> None:
        self._classrooms = classroom_repo
        self._enrollments = enrollment_repo
        self._members = member_repo
        self._syllabus = syllabus_repo
        self._users = user_repo
        self._code_len = join_code_length

    # ── Teacher / staff ──────────────────────────────────────────────────────

    async def create_classroom(
        self,
        teacher_id: UUID,
        school_id: UUID,
        name: str,
        subject: str | None,
        grade: str | None,
        description: str | None,
    ) -> Classroom:
        if not await self._members.get(school_id, teacher_id):
            raise AuthorizationError("You are not a member of this school")

        classroom = await self._classrooms.create(
            Classroom(
                school_id=school_id,
                name=name,
                subject=subject,
                grade=grade,
                teacher_id=teacher_id,
                join_code=await self._unique_code(),
                description=description,
            )
        )
        logger.info("classroom_created", classroom_id=str(classroom.id))
        return classroom

    async def list_my_classrooms(self, teacher_id: UUID) -> list[Classroom]:
        return await self._classrooms.list_by_teacher(teacher_id)

    async def get_for_manage(self, classroom_id: UUID, user_id: UUID) -> Classroom:
        classroom = await self._classrooms.get_by_id(classroom_id)
        if not classroom:
            raise EntityNotFound("Classroom not found")
        await self._assert_can_manage(classroom, user_id)
        return classroom

    async def update_classroom(
        self,
        classroom_id: UUID,
        user_id: UUID,
        name: str | None,
        subject: str | None,
        grade: str | None,
        description: str | None,
        is_active: bool | None,
    ) -> Classroom:
        classroom = await self.get_for_manage(classroom_id, user_id)
        if name is not None:
            classroom.name = name
        if subject is not None:
            classroom.subject = subject
        if grade is not None:
            classroom.grade = grade
        if description is not None:
            classroom.description = description
        if is_active is not None:
            classroom.is_active = is_active
        return await self._classrooms.update(classroom)

    async def delete_classroom(self, classroom_id: UUID, user_id: UUID) -> None:
        await self.get_for_manage(classroom_id, user_id)
        await self._classrooms.delete(classroom_id)

    async def roster(
        self, classroom_id: UUID, user_id: UUID
    ) -> list[tuple[Enrollment, str, str]]:
        await self.get_for_manage(classroom_id, user_id)
        enrollments = await self._enrollments.list_by_classroom(classroom_id)
        out: list[tuple[Enrollment, str, str]] = []
        for e in enrollments:
            student = await self._users.get_by_id(e.student_id)
            if student:
                out.append((e, student.username, student.email))
        return out

    # ── Student ──────────────────────────────────────────────────────────────

    async def join_by_code(self, student_id: UUID, join_code: str) -> Classroom:
        classroom = await self._classrooms.get_by_join_code(join_code.strip().upper())
        if not classroom or not classroom.is_active:
            raise EntityNotFound("No active classroom found for that code")

        existing = await self._enrollments.get(classroom.id, student_id)
        if existing and existing.status == "active":
            return classroom
        if existing:
            existing.status = "active"
            await self._enrollments.update(existing)
        else:
            await self._enrollments.create(
                Enrollment(classroom_id=classroom.id, student_id=student_id)
            )
        logger.info(
            "student_joined_classroom",
            classroom_id=str(classroom.id),
            student_id=str(student_id),
        )
        return classroom

    async def list_enrolled(self, student_id: UUID) -> list[Classroom]:
        enrollments = await self._enrollments.list_by_student(student_id)
        ids = [e.classroom_id for e in enrollments]
        classrooms = await self._classrooms.list_by_ids(ids)
        return [c for c in classrooms if c.is_active]

    async def assert_enrolled(self, classroom_id: UUID, student_id: UUID) -> None:
        enrollment = await self._enrollments.get(classroom_id, student_id)
        if not enrollment or enrollment.status != "active":
            raise AuthorizationError("You are not enrolled in this classroom")

    async def resolve_kb_for_student(
        self, student_id: UUID, subject: str | None = None
    ) -> UUID | None:
        """The knowledge base of the student's enrolled class for this subject
        (or their first class with materials), so the tutor grounds answers in
        the teacher's uploads. Returns None when the student has no such class."""
        classrooms = await self.list_enrolled(student_id)
        with_kb = [c for c in classrooms if c.knowledge_base_id]
        if not with_kb:
            return None
        if subject:
            target = subject.strip().lower()
            for c in with_kb:
                if (c.subject or "").strip().lower() == target:
                    return c.knowledge_base_id
        return with_kb[0].knowledge_base_id

    # ── Counts (for response DTOs) ───────────────────────────────────────────

    async def counts(self, classroom_id: UUID) -> tuple[int, int]:
        students = await self._enrollments.count_by_classroom(classroom_id)
        syllabus = await self._syllabus.list_by_classroom(classroom_id)
        return students, len(syllabus)

    # ── Internals ────────────────────────────────────────────────────────────

    async def _assert_can_manage(self, classroom: Classroom, user_id: UUID) -> None:
        if classroom.teacher_id == user_id:
            return
        member = await self._members.get(classroom.school_id, user_id)
        if member and member.role == Role.SCHOOL_ADMIN:
            return
        raise AuthorizationError("You do not manage this classroom")

    async def _unique_code(self) -> str:
        for _ in range(10):
            code = "".join(secrets.choice(_CODE_ALPHABET) for _ in range(self._code_len))
            if not await self._classrooms.get_by_join_code(code):
                return code
        raise ValidationError("Could not allocate a unique join code")
