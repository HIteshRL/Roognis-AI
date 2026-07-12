"""
Teacher persona orchestration (Google Classroom model).

A teacher creates classrooms (their "subjects"), adds ordered chapters, and
shares a join code. Students enrol with the code and run chapter-scoped
inference. Each chapter wraps a KnowledgeBase, so teacher content upload and
student RAG reuse the existing document/retrieval stack unchanged.
"""
import secrets
from uuid import UUID

import structlog

from src.application.dtos.classroom import (
    ChapterResponse,
    ClassroomResponse,
    CoTeacherResponse,
    CreateChapterRequest,
    CreateClassroomRequest,
    EnrolledStudentResponse,
    InvitationResponse,
    PendingEnrollmentResponse,
    StudentClassroomResponse,
    UpdateChapterRequest,
    UpdateClassroomRequest,
)
from src.domain.entities.classroom import (
    CLASSROOM_COLORS,
    Chapter,
    Classroom,
    Enrollment,
    generate_join_code,
)
from src.domain.entities.knowledge import KnowledgeBase
from src.domain.entities.lms import ClassroomInvitation, ClassroomTeacher
from src.domain.exceptions import AuthorizationError, DuplicateEntity, EntityNotFound
from src.domain.repositories.classroom_repository import (
    AbstractChapterRepository,
    AbstractClassroomRepository,
    AbstractEnrollmentRepository,
)
from src.domain.repositories.knowledge_repository import (
    AbstractDocumentRepository,
    AbstractKnowledgeBaseRepository,
)
from src.domain.repositories.lms_repository import (
    AbstractClassroomTeacherRepository,
    AbstractInvitationRepository,
)
from src.domain.repositories.user_repository import AbstractUserRepository

logger = structlog.get_logger(__name__)

_JOIN_CODE_MAX_ATTEMPTS = 6


class ClassroomService:
    def __init__(
        self,
        classroom_repo: AbstractClassroomRepository,
        chapter_repo: AbstractChapterRepository,
        enrollment_repo: AbstractEnrollmentRepository,
        kb_repo: AbstractKnowledgeBaseRepository,
        user_repo: AbstractUserRepository,
        doc_repo: AbstractDocumentRepository,
        teacher_repo: AbstractClassroomTeacherRepository | None = None,
        invitation_repo: AbstractInvitationRepository | None = None,
        notification_svc=None,  # NotificationService; Any to avoid intra-package import
    ) -> None:
        self._classrooms = classroom_repo
        self._chapters = chapter_repo
        self._enrollments = enrollment_repo
        self._kbs = kb_repo
        self._users = user_repo
        self._docs = doc_repo
        self._teachers = teacher_repo
        self._invitations = invitation_repo
        self._notify = notification_svc

    # ── Classrooms ───────────────────────────────────────────────────────────

    async def create_classroom(
        self, teacher_id: UUID, dto: CreateClassroomRequest
    ) -> ClassroomResponse:
        existing = await self._classrooms.list_by_teacher(teacher_id, include_archived=True)
        color = dto.color or CLASSROOM_COLORS[len(existing) % len(CLASSROOM_COLORS)]

        classroom = Classroom(
            teacher_id=teacher_id,
            name=dto.name,
            subject=dto.subject,
            section=dto.section,
            room=dto.room,
            grade=dto.grade,
            description=dto.description,
            color=color,
            join_code=await self._unique_join_code(),
            semester=dto.semester,
            institution_id=UUID(dto.institution_id) if dto.institution_id else None,
            banner_url=dto.banner_url,
            settings=dto.settings or {},
        )
        classroom = await self._classrooms.create(classroom)
        if self._teachers:
            await self._teachers.add(
                ClassroomTeacher(classroom_id=classroom.id, teacher_id=teacher_id, role="owner")
            )
        logger.info("classroom_created", classroom_id=str(classroom.id), teacher_id=str(teacher_id))
        return self._classroom_to_response(classroom, student_count=0, chapter_count=0)

    async def list_teacher_classrooms(self, teacher_id: UUID) -> list[ClassroomResponse]:
        classrooms = await self._classrooms.list_by_teacher(teacher_id)
        seen = {c.id for c in classrooms}
        if self._teachers:
            for classroom_id in await self._teachers.list_classroom_ids_for_teacher(teacher_id):
                if classroom_id in seen:
                    continue
                co_taught = await self._classrooms.get_by_id(classroom_id)
                if co_taught and not co_taught.is_archived and not co_taught.is_deleted:
                    classrooms.append(co_taught)
        out: list[ClassroomResponse] = []
        for c in classrooms:
            if c.is_deleted:
                continue
            students = await self._classrooms.count_students(c.id)
            chapters = await self._classrooms.count_chapters(c.id)
            out.append(self._classroom_to_response(c, students, chapters))
        return out

    async def get_classroom_for_teacher(
        self, teacher_id: UUID, classroom_id: UUID
    ) -> ClassroomResponse:
        classroom = await self._owned_classroom(teacher_id, classroom_id)
        students = await self._classrooms.count_students(classroom.id)
        chapters = await self._classrooms.count_chapters(classroom.id)
        return self._classroom_to_response(classroom, students, chapters)

    async def update_classroom(
        self, teacher_id: UUID, classroom_id: UUID, dto: UpdateClassroomRequest
    ) -> ClassroomResponse:
        classroom = await self._owned_classroom(teacher_id, classroom_id)
        for field_name in (
            "name", "subject", "section", "room", "grade", "description", "color",
            "semester", "banner_url", "settings",
        ):
            value = getattr(dto, field_name)
            if value is not None:
                setattr(classroom, field_name, value)
        if dto.institution_id is not None:
            classroom.institution_id = UUID(dto.institution_id) if dto.institution_id else None
        classroom = await self._classrooms.update(classroom)
        students = await self._classrooms.count_students(classroom.id)
        chapters = await self._classrooms.count_chapters(classroom.id)
        return self._classroom_to_response(classroom, students, chapters)

    async def delete_classroom(self, teacher_id: UUID, classroom_id: UUID) -> None:
        """Soft delete — owner only. Data stays recoverable by an admin."""
        classroom = await self._classrooms.get_by_id(classroom_id)
        if not classroom or classroom.is_deleted:
            raise EntityNotFound("Classroom not found")
        if classroom.teacher_id != teacher_id:
            raise AuthorizationError("Only the classroom owner can delete it")
        classroom.soft_delete()
        await self._classrooms.update(classroom)
        logger.info("classroom_deleted", classroom_id=str(classroom_id))

    async def set_join_code_enabled(
        self, teacher_id: UUID, classroom_id: UUID, enabled: bool
    ) -> ClassroomResponse:
        classroom = await self._owned_classroom(teacher_id, classroom_id)
        classroom.join_code_enabled = enabled
        classroom = await self._classrooms.update(classroom)
        students = await self._classrooms.count_students(classroom.id)
        chapters = await self._classrooms.count_chapters(classroom.id)
        return self._classroom_to_response(classroom, students, chapters)

    async def archive_classroom(self, teacher_id: UUID, classroom_id: UUID) -> None:
        classroom = await self._owned_classroom(teacher_id, classroom_id)
        classroom.archive()
        await self._classrooms.update(classroom)

    async def regenerate_join_code(self, teacher_id: UUID, classroom_id: UUID) -> ClassroomResponse:
        classroom = await self._owned_classroom(teacher_id, classroom_id)
        classroom.join_code = await self._unique_join_code()
        classroom = await self._classrooms.update(classroom)
        students = await self._classrooms.count_students(classroom.id)
        chapters = await self._classrooms.count_chapters(classroom.id)
        return self._classroom_to_response(classroom, students, chapters)

    # ── Co-teachers & invitations ────────────────────────────────────────────

    async def invite(
        self, teacher_id: UUID, classroom_id: UUID, email: str, role: str
    ) -> InvitationResponse:
        if not self._invitations:
            raise EntityNotFound("Invitations are not enabled")
        classroom = await self._owned_classroom(teacher_id, classroom_id)
        invitation = await self._invitations.create(
            ClassroomInvitation(
                classroom_id=classroom_id,
                email=email,
                invited_by=teacher_id,
                role=role,
                token=secrets.token_urlsafe(24),
            )
        )
        invitee = await self._users.get_by_email(email)
        if invitee and self._notify:
            await self._notify.emit(
                user_id=invitee.id,
                type="classroom_invitation",
                title=f"You've been invited to {classroom.name}",
                body=f"Role: {role.replace('_', ' ')}",
                data={"classroom_id": str(classroom_id), "invitation_id": str(invitation.id)},
            )
        logger.info(
            "classroom_invited", classroom_id=str(classroom_id), role=role,
        )
        return self._invitation_to_response(invitation)

    async def list_invitations(
        self, teacher_id: UUID, classroom_id: UUID, status: str | None = None
    ) -> list[InvitationResponse]:
        if not self._invitations:
            return []
        await self._owned_classroom(teacher_id, classroom_id)
        invitations = await self._invitations.list_by_classroom(classroom_id, status=status)
        return [self._invitation_to_response(i) for i in invitations]

    async def revoke_invitation(self, teacher_id: UUID, invitation_id: UUID) -> None:
        if not self._invitations:
            raise EntityNotFound("Invitations are not enabled")
        invitation = await self._invitations.get_by_id(invitation_id)
        if not invitation:
            raise EntityNotFound("Invitation not found")
        await self._owned_classroom(teacher_id, invitation.classroom_id)
        invitation.status = "revoked"
        await self._invitations.update(invitation)

    async def my_invitations(self, user_id: UUID) -> list[InvitationResponse]:
        if not self._invitations:
            return []
        user = await self._users.get_by_id(user_id)
        if not user:
            return []
        invitations = await self._invitations.list_pending_for_email(user.email)
        return [self._invitation_to_response(i) for i in invitations]

    async def respond_to_invitation(
        self, user_id: UUID, invitation_id: UUID, accept: bool
    ) -> None:
        if not self._invitations:
            raise EntityNotFound("Invitations are not enabled")
        invitation = await self._invitations.get_by_id(invitation_id)
        user = await self._users.get_by_id(user_id)
        if (
            not invitation
            or not user
            or not invitation.is_pending
            or invitation.email.lower() != user.email.lower()
        ):
            raise EntityNotFound("Invitation not found")

        invitation.status = "accepted" if accept else "rejected"
        await self._invitations.update(invitation)
        if not accept:
            return

        if invitation.role == "co_teacher":
            if self._teachers and not await self._teachers.get(invitation.classroom_id, user_id):
                await self._teachers.add(
                    ClassroomTeacher(
                        classroom_id=invitation.classroom_id,
                        teacher_id=user_id,
                        role="co_teacher",
                    )
                )
        else:
            existing = await self._enrollments.get(invitation.classroom_id, user_id)
            if existing:
                await self._enrollments.set_status(invitation.classroom_id, user_id, "active")
            else:
                await self._enrollments.create(
                    Enrollment(classroom_id=invitation.classroom_id, student_id=user_id)
                )
        if self._notify:
            await self._notify.emit(
                user_id=invitation.invited_by,
                type="invitation_accepted",
                title=f"{user.username} accepted your invitation",
                data={"classroom_id": str(invitation.classroom_id)},
            )

    async def list_co_teachers(
        self, teacher_id: UUID, classroom_id: UUID
    ) -> list[CoTeacherResponse]:
        if not self._teachers:
            return []
        await self._owned_classroom(teacher_id, classroom_id)
        out: list[CoTeacherResponse] = []
        for membership in await self._teachers.list_by_classroom(classroom_id):
            user = await self._users.get_by_id(membership.teacher_id)
            if user:
                out.append(
                    CoTeacherResponse(
                        id=str(user.id),
                        username=user.username,
                        email=user.email,
                        role=membership.role,
                        added_at=membership.created_at.isoformat(),
                    )
                )
        return out

    async def remove_co_teacher(
        self, teacher_id: UUID, classroom_id: UUID, co_teacher_id: UUID
    ) -> None:
        if not self._teachers:
            raise EntityNotFound("Co-teaching is not enabled")
        classroom = await self._classrooms.get_by_id(classroom_id)
        if not classroom or classroom.is_deleted:
            raise EntityNotFound("Classroom not found")
        if classroom.teacher_id != teacher_id:
            raise AuthorizationError("Only the classroom owner can remove teachers")
        if co_teacher_id == classroom.teacher_id:
            raise AuthorizationError("The owner cannot be removed")
        await self._teachers.remove(classroom_id, co_teacher_id)

    # ── Enrollment approval ──────────────────────────────────────────────────

    async def list_pending_enrollments(
        self, teacher_id: UUID, classroom_id: UUID
    ) -> list[PendingEnrollmentResponse]:
        await self._owned_classroom(teacher_id, classroom_id)
        students = await self._enrollments.list_students(classroom_id, status="pending")
        out: list[PendingEnrollmentResponse] = []
        for user in students:
            enrollment = await self._enrollments.get(classroom_id, user.id)
            out.append(
                PendingEnrollmentResponse(
                    student_id=str(user.id),
                    username=user.username,
                    email=user.email,
                    requested_at=enrollment.joined_at.isoformat() if enrollment else "",
                )
            )
        return out

    async def approve_enrollment(
        self, teacher_id: UUID, classroom_id: UUID, student_id: UUID
    ) -> None:
        classroom = await self._owned_classroom(teacher_id, classroom_id)
        enrollment = await self._enrollments.get(classroom_id, student_id)
        if not enrollment or enrollment.status != "pending":
            raise EntityNotFound("No pending join request for that student")
        await self._enrollments.set_status(classroom_id, student_id, "active")
        if self._notify:
            await self._notify.emit(
                user_id=student_id,
                type="enrollment_approved",
                title=f"You're in! {classroom.name} approved your request",
                data={"classroom_id": str(classroom_id)},
            )

    async def reject_enrollment(
        self, teacher_id: UUID, classroom_id: UUID, student_id: UUID
    ) -> None:
        classroom = await self._owned_classroom(teacher_id, classroom_id)
        enrollment = await self._enrollments.get(classroom_id, student_id)
        if not enrollment or enrollment.status != "pending":
            raise EntityNotFound("No pending join request for that student")
        await self._enrollments.delete(classroom_id, student_id)
        if self._notify:
            await self._notify.emit(
                user_id=student_id,
                type="enrollment_rejected",
                title=f"Your request to join {classroom.name} was declined",
                data={"classroom_id": str(classroom_id)},
            )

    async def leave_classroom(self, student_id: UUID, classroom_id: UUID) -> None:
        enrollment = await self._enrollments.get(classroom_id, student_id)
        if not enrollment:
            raise EntityNotFound("You are not enrolled in this class")
        await self._enrollments.delete(classroom_id, student_id)
        logger.info(
            "student_left", classroom_id=str(classroom_id), student_id=str(student_id)
        )

    # ── Chapters ─────────────────────────────────────────────────────────────

    async def add_chapter(
        self, teacher_id: UUID, classroom_id: UUID, dto: CreateChapterRequest
    ) -> ChapterResponse:
        classroom = await self._owned_classroom(teacher_id, classroom_id)

        # Each chapter gets its own KnowledgeBase so uploaded content is
        # retrievable in isolation — student inference scopes to this KB.
        kb = await self._kbs.create(
            KnowledgeBase(
                name=f"{classroom.name} — {dto.title}",
                created_by=teacher_id,
                description=dto.description,
                subject=classroom.subject,
                grade=classroom.grade,
                chapter=dto.title,
            )
        )

        order = await self._chapters.next_order_index(classroom_id)
        chapter = await self._chapters.create(
            Chapter(
                classroom_id=classroom_id,
                title=dto.title,
                description=dto.description,
                knowledge_base_id=kb.id,
                order_index=order,
            )
        )
        logger.info("chapter_created", chapter_id=str(chapter.id), classroom_id=str(classroom_id))
        return self._chapter_to_response(chapter, document_count=0)

    async def list_chapters(self, classroom_id: UUID) -> list[ChapterResponse]:
        chapters = await self._chapters.list_by_classroom(classroom_id)
        out: list[ChapterResponse] = []
        for ch in chapters:
            out.append(self._chapter_to_response(ch, await self._chapter_doc_count(ch)))
        return out

    async def update_chapter(
        self, teacher_id: UUID, chapter_id: UUID, dto: UpdateChapterRequest
    ) -> ChapterResponse:
        chapter = await self._owned_chapter(teacher_id, chapter_id)
        if dto.title is not None:
            chapter.title = dto.title
        if dto.description is not None:
            chapter.description = dto.description
        if dto.is_published is not None:
            chapter.is_published = dto.is_published
        if dto.order_index is not None:
            chapter.order_index = dto.order_index
        chapter = await self._chapters.update(chapter)
        return self._chapter_to_response(chapter, await self._chapter_doc_count(chapter))

    async def delete_chapter(self, teacher_id: UUID, chapter_id: UUID) -> None:
        chapter = await self._owned_chapter(teacher_id, chapter_id)
        await self._chapters.delete(chapter.id)

    async def get_chapter_kb_for_teacher(
        self, teacher_id: UUID, chapter_id: UUID
    ) -> UUID | None:
        chapter = await self._owned_chapter(teacher_id, chapter_id)
        return chapter.knowledge_base_id

    # ── Enrollment (student side) ────────────────────────────────────────────

    async def join_by_code(self, student_id: UUID, join_code: str) -> StudentClassroomResponse:
        classroom = await self._classrooms.get_by_join_code(join_code.strip().upper())
        if (
            not classroom
            or classroom.is_archived
            or classroom.is_deleted
            or not classroom.join_code_enabled
        ):
            raise EntityNotFound("No class found for that code")

        existing = await self._enrollments.get(classroom.id, student_id)
        if existing and existing.status == "pending":
            raise DuplicateEntity("Your join request is awaiting teacher approval")
        if not existing:
            requires_approval = bool(classroom.settings.get("require_approval"))
            status = "pending" if requires_approval else "active"
            await self._enrollments.create(
                Enrollment(classroom_id=classroom.id, student_id=student_id, status=status)
            )
            student = await self._users.get_by_id(student_id)
            if self._notify and student:
                await self._notify.emit(
                    user_id=classroom.teacher_id,
                    type="student_join_request" if requires_approval else "student_joined",
                    title=(
                        f"{student.username} requested to join {classroom.name}"
                        if requires_approval
                        else f"{student.username} joined {classroom.name}"
                    ),
                    data={"classroom_id": str(classroom.id), "student_id": str(student_id)},
                )
            logger.info(
                "student_enrolled",
                classroom_id=str(classroom.id),
                student_id=str(student_id),
                status=status,
            )
        elif existing.status == "removed":
            await self._enrollments.set_status(classroom.id, student_id, "active")
        return await self._student_classroom_response(classroom)

    async def list_student_classrooms(self, student_id: UUID) -> list[StudentClassroomResponse]:
        classrooms = await self._enrollments.list_classrooms_for_student(student_id)
        return [await self._student_classroom_response(c) for c in classrooms]

    async def list_students(
        self, teacher_id: UUID, classroom_id: UUID
    ) -> list[EnrolledStudentResponse]:
        await self._owned_classroom(teacher_id, classroom_id)
        students = await self._enrollments.list_students(classroom_id)
        # joined_at lives on the enrollment; fetch per-student to render join time.
        out: list[EnrolledStudentResponse] = []
        for user in students:
            enrollment = await self._enrollments.get(classroom_id, user.id)
            out.append(
                EnrolledStudentResponse(
                    id=str(user.id),
                    username=user.username,
                    email=user.email,
                    joined_at=enrollment.joined_at.isoformat() if enrollment else "",
                )
            )
        return out

    async def remove_student(
        self, teacher_id: UUID, classroom_id: UUID, student_id: UUID
    ) -> None:
        await self._owned_classroom(teacher_id, classroom_id)
        await self._enrollments.delete(classroom_id, student_id)

    async def list_chapters_for_student(
        self, student_id: UUID, classroom_id: UUID
    ) -> list[ChapterResponse]:
        if not await self._enrollments.is_enrolled(classroom_id, student_id):
            raise AuthorizationError("You are not enrolled in this class")
        chapters = await self._chapters.list_by_classroom(classroom_id)
        return [
            self._chapter_to_response(ch, await self._chapter_doc_count(ch))
            for ch in chapters
            if ch.is_published
        ]

    async def resolve_chapter_kb_for_student(
        self, student_id: UUID, chapter_id: UUID
    ) -> UUID | None:
        """Return the chapter's KB id if the student may access it (enrolled).

        Used by the chat route to scope inference to a chapter. Raises if the
        chapter is missing or the student is not enrolled in its classroom.
        """
        chapter = await self._chapters.get_by_id(chapter_id)
        if not chapter or not chapter.is_published:
            raise EntityNotFound("Chapter not found")
        if not await self._enrollments.is_enrolled(chapter.classroom_id, student_id):
            raise AuthorizationError("You are not enrolled in this class")
        return chapter.knowledge_base_id

    # ── Helpers ──────────────────────────────────────────────────────────────

    async def _unique_join_code(self) -> str:
        for _ in range(_JOIN_CODE_MAX_ATTEMPTS):
            code = generate_join_code()
            if not await self._classrooms.get_by_join_code(code):
                return code
        # Astronomically unlikely; last generated code still almost certainly free.
        return generate_join_code()

    async def _owned_classroom(self, teacher_id: UUID, classroom_id: UUID) -> Classroom:
        """The classroom, if the caller teaches it (owner or co-teacher)."""
        classroom = await self._classrooms.get_by_id(classroom_id)
        if not classroom or classroom.is_deleted:
            raise EntityNotFound("Classroom not found")
        if classroom.teacher_id == teacher_id:
            return classroom
        if self._teachers and await self._teachers.get(classroom_id, teacher_id):
            return classroom
        raise AuthorizationError("You do not teach this classroom")

    async def _owned_chapter(self, teacher_id: UUID, chapter_id: UUID) -> Chapter:
        chapter = await self._chapters.get_by_id(chapter_id)
        if not chapter:
            raise EntityNotFound("Chapter not found")
        await self._owned_classroom(teacher_id, chapter.classroom_id)
        return chapter

    async def _chapter_doc_count(self, chapter: Chapter) -> int:
        if not chapter.knowledge_base_id:
            return 0
        _docs, total = await self._docs.list_by_knowledge_base(
            chapter.knowledge_base_id, page=1, limit=1
        )
        return total

    async def _student_classroom_response(self, classroom: Classroom) -> StudentClassroomResponse:
        teacher = await self._users.get_by_id(classroom.teacher_id)
        chapters = await self._classrooms.count_chapters(classroom.id)
        return StudentClassroomResponse(
            id=str(classroom.id),
            name=classroom.name,
            subject=classroom.subject,
            section=classroom.section,
            grade=classroom.grade,
            color=classroom.color,
            teacher_name=teacher.username if teacher else "Teacher",
            chapter_count=chapters,
            created_at=classroom.created_at.isoformat(),
        )

    @staticmethod
    def _classroom_to_response(
        c: Classroom, student_count: int, chapter_count: int
    ) -> ClassroomResponse:
        return ClassroomResponse(
            id=str(c.id),
            teacher_id=str(c.teacher_id),
            name=c.name,
            subject=c.subject,
            section=c.section,
            room=c.room,
            grade=c.grade,
            description=c.description,
            color=c.color,
            join_code=c.join_code,
            is_archived=c.is_archived,
            semester=c.semester,
            institution_id=str(c.institution_id) if c.institution_id else None,
            banner_url=c.banner_url,
            settings=c.settings,
            join_code_enabled=c.join_code_enabled,
            student_count=student_count,
            chapter_count=chapter_count,
            created_at=c.created_at.isoformat(),
            updated_at=c.updated_at.isoformat(),
        )

    @staticmethod
    def _invitation_to_response(i: ClassroomInvitation) -> InvitationResponse:
        return InvitationResponse(
            id=str(i.id),
            classroom_id=str(i.classroom_id),
            email=i.email,
            role=i.role,
            status=i.status,
            invited_by=str(i.invited_by),
            created_at=i.created_at.isoformat(),
        )

    @staticmethod
    def _chapter_to_response(ch: Chapter, document_count: int) -> ChapterResponse:
        return ChapterResponse(
            id=str(ch.id),
            classroom_id=str(ch.classroom_id),
            knowledge_base_id=str(ch.knowledge_base_id) if ch.knowledge_base_id else None,
            title=ch.title,
            description=ch.description,
            order_index=ch.order_index,
            is_published=ch.is_published,
            document_count=document_count,
            created_at=ch.created_at.isoformat(),
            updated_at=ch.updated_at.isoformat(),
        )
