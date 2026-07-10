"""
Teacher persona orchestration (Google Classroom model).

A teacher creates classrooms (their "subjects"), adds ordered chapters, and
shares a join code. Students enrol with the code and run chapter-scoped
inference. Each chapter wraps a KnowledgeBase, so teacher content upload and
student RAG reuse the existing document/retrieval stack unchanged.
"""
from uuid import UUID

import structlog

from src.application.dtos.classroom import (
    ChapterResponse,
    ClassroomResponse,
    CreateChapterRequest,
    CreateClassroomRequest,
    EnrolledStudentResponse,
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
from src.domain.exceptions import AuthorizationError, EntityNotFound
from src.domain.repositories.classroom_repository import (
    AbstractChapterRepository,
    AbstractClassroomRepository,
    AbstractEnrollmentRepository,
)
from src.domain.repositories.knowledge_repository import (
    AbstractDocumentRepository,
    AbstractKnowledgeBaseRepository,
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
    ) -> None:
        self._classrooms = classroom_repo
        self._chapters = chapter_repo
        self._enrollments = enrollment_repo
        self._kbs = kb_repo
        self._users = user_repo
        self._docs = doc_repo

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
        )
        classroom = await self._classrooms.create(classroom)
        logger.info("classroom_created", classroom_id=str(classroom.id), teacher_id=str(teacher_id))
        return self._classroom_to_response(classroom, student_count=0, chapter_count=0)

    async def list_teacher_classrooms(self, teacher_id: UUID) -> list[ClassroomResponse]:
        classrooms = await self._classrooms.list_by_teacher(teacher_id)
        out: list[ClassroomResponse] = []
        for c in classrooms:
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
        for field_name in ("name", "subject", "section", "room", "grade", "description", "color"):
            value = getattr(dto, field_name)
            if value is not None:
                setattr(classroom, field_name, value)
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
        if not classroom or classroom.is_archived:
            raise EntityNotFound("No class found for that code")

        if not await self._enrollments.is_enrolled(classroom.id, student_id):
            await self._enrollments.create(
                Enrollment(classroom_id=classroom.id, student_id=student_id)
            )
            logger.info(
                "student_enrolled", classroom_id=str(classroom.id), student_id=str(student_id)
            )
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
        classroom = await self._classrooms.get_by_id(classroom_id)
        if not classroom:
            raise EntityNotFound("Classroom not found")
        if classroom.teacher_id != teacher_id:
            raise AuthorizationError("You do not own this classroom")
        return classroom

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
            student_count=student_count,
            chapter_count=chapter_count,
            created_at=c.created_at.isoformat(),
            updated_at=c.updated_at.isoformat(),
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
