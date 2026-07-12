from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.classroom import Chapter, Classroom, Enrollment
from src.domain.entities.user import User
from src.domain.repositories.classroom_repository import (
    AbstractChapterRepository,
    AbstractClassroomRepository,
    AbstractEnrollmentRepository,
)
from src.infrastructure.database.models.classroom import (
    ChapterModel,
    ClassroomModel,
    EnrollmentModel,
)
from src.infrastructure.database.models.user import UserModel
from src.infrastructure.database.repositories.user_repository import _to_entity as _user_to_entity


def _classroom_to_entity(m: ClassroomModel) -> Classroom:
    c = Classroom.__new__(Classroom)
    c.id = UUID(m.id)
    c.teacher_id = UUID(m.teacher_id)
    c.name = m.name
    c.subject = m.subject
    c.section = m.section
    c.room = m.room
    c.grade = m.grade
    c.description = m.description
    c.color = m.color
    c.join_code = m.join_code
    c.is_archived = m.is_archived
    c.semester = m.semester
    c.institution_id = UUID(m.institution_id) if m.institution_id else None
    c.banner_url = m.banner_url
    c.settings = m.settings or {}
    c.join_code_enabled = m.join_code_enabled
    c.is_deleted = m.is_deleted
    c.deleted_at = m.deleted_at
    c.created_at = m.created_at
    c.updated_at = m.updated_at
    return c


def _chapter_to_entity(m: ChapterModel) -> Chapter:
    ch = Chapter.__new__(Chapter)
    ch.id = UUID(m.id)
    ch.classroom_id = UUID(m.classroom_id)
    ch.knowledge_base_id = UUID(m.knowledge_base_id) if m.knowledge_base_id else None
    ch.title = m.title
    ch.description = m.description
    ch.order_index = m.order_index
    ch.is_published = m.is_published
    ch.created_at = m.created_at
    ch.updated_at = m.updated_at
    return ch


def _enrollment_to_entity(m: EnrollmentModel) -> Enrollment:
    e = Enrollment.__new__(Enrollment)
    e.id = UUID(m.id)
    e.classroom_id = UUID(m.classroom_id)
    e.student_id = UUID(m.student_id)
    e.status = m.status
    e.joined_at = m.joined_at
    e.created_at = m.created_at
    e.updated_at = m.updated_at
    return e


class ClassroomRepository(AbstractClassroomRepository):
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(self, classroom: Classroom) -> Classroom:
        model = ClassroomModel(
            id=str(classroom.id),
            teacher_id=str(classroom.teacher_id),
            name=classroom.name,
            subject=classroom.subject,
            section=classroom.section,
            room=classroom.room,
            grade=classroom.grade,
            description=classroom.description,
            color=classroom.color,
            join_code=classroom.join_code,
            is_archived=classroom.is_archived,
            semester=classroom.semester,
            institution_id=str(classroom.institution_id) if classroom.institution_id else None,
            banner_url=classroom.banner_url,
            settings=classroom.settings,
            join_code_enabled=classroom.join_code_enabled,
            is_deleted=classroom.is_deleted,
            deleted_at=classroom.deleted_at,
        )
        self._db.add(model)
        await self._db.flush()
        await self._db.refresh(model)
        return _classroom_to_entity(model)

    async def get_by_id(self, classroom_id: UUID) -> Classroom | None:
        result = await self._db.execute(
            select(ClassroomModel).where(ClassroomModel.id == str(classroom_id))
        )
        model = result.scalar_one_or_none()
        return _classroom_to_entity(model) if model else None

    async def get_by_join_code(self, join_code: str) -> Classroom | None:
        result = await self._db.execute(
            select(ClassroomModel).where(ClassroomModel.join_code == join_code)
        )
        model = result.scalar_one_or_none()
        return _classroom_to_entity(model) if model else None

    async def list_by_teacher(
        self, teacher_id: UUID, include_archived: bool = False
    ) -> list[Classroom]:
        stmt = select(ClassroomModel).where(ClassroomModel.teacher_id == str(teacher_id))
        if not include_archived:
            stmt = stmt.where(ClassroomModel.is_archived.is_(False))
        stmt = stmt.order_by(ClassroomModel.created_at.desc())
        result = await self._db.execute(stmt)
        return [_classroom_to_entity(m) for m in result.scalars().all()]

    async def update(self, classroom: Classroom) -> Classroom:
        result = await self._db.execute(
            select(ClassroomModel).where(ClassroomModel.id == str(classroom.id))
        )
        model = result.scalar_one()
        model.name = classroom.name
        model.subject = classroom.subject
        model.section = classroom.section
        model.room = classroom.room
        model.grade = classroom.grade
        model.description = classroom.description
        model.color = classroom.color
        model.join_code = classroom.join_code
        model.is_archived = classroom.is_archived
        model.semester = classroom.semester
        model.institution_id = (
            str(classroom.institution_id) if classroom.institution_id else None
        )
        model.banner_url = classroom.banner_url
        model.settings = classroom.settings
        model.join_code_enabled = classroom.join_code_enabled
        model.is_deleted = classroom.is_deleted
        model.deleted_at = classroom.deleted_at
        await self._db.flush()
        await self._db.refresh(model)
        return _classroom_to_entity(model)

    async def delete(self, classroom_id: UUID) -> None:
        result = await self._db.execute(
            select(ClassroomModel).where(ClassroomModel.id == str(classroom_id))
        )
        model = result.scalar_one_or_none()
        if model:
            await self._db.delete(model)
            await self._db.flush()

    async def list_all(
        self,
        page: int = 1,
        limit: int = 50,
        search: str | None = None,
        include_deleted: bool = False,
    ) -> tuple[list[Classroom], int]:
        stmt = select(ClassroomModel)
        if search:
            stmt = stmt.where(ClassroomModel.name.ilike(f"%{search}%"))
        if not include_deleted:
            stmt = stmt.where(ClassroomModel.is_deleted.is_(False))
        total = (
            await self._db.execute(select(func.count()).select_from(stmt.subquery()))
        ).scalar_one()
        stmt = (
            stmt.order_by(ClassroomModel.created_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        )
        rows = (await self._db.execute(stmt)).scalars().all()
        return [_classroom_to_entity(m) for m in rows], int(total)

    async def count_students(self, classroom_id: UUID) -> int:
        result = await self._db.execute(
            select(func.count())
            .select_from(EnrollmentModel)
            .where(
                EnrollmentModel.classroom_id == str(classroom_id),
                EnrollmentModel.status == "active",
            )
        )
        return int(result.scalar_one())

    async def count_chapters(self, classroom_id: UUID) -> int:
        result = await self._db.execute(
            select(func.count())
            .select_from(ChapterModel)
            .where(ChapterModel.classroom_id == str(classroom_id))
        )
        return int(result.scalar_one())


class ChapterRepository(AbstractChapterRepository):
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(self, chapter: Chapter) -> Chapter:
        model = ChapterModel(
            id=str(chapter.id),
            classroom_id=str(chapter.classroom_id),
            knowledge_base_id=str(chapter.knowledge_base_id) if chapter.knowledge_base_id else None,
            title=chapter.title,
            description=chapter.description,
            order_index=chapter.order_index,
            is_published=chapter.is_published,
        )
        self._db.add(model)
        await self._db.flush()
        await self._db.refresh(model)
        return _chapter_to_entity(model)

    async def get_by_id(self, chapter_id: UUID) -> Chapter | None:
        result = await self._db.execute(
            select(ChapterModel).where(ChapterModel.id == str(chapter_id))
        )
        model = result.scalar_one_or_none()
        return _chapter_to_entity(model) if model else None

    async def list_by_classroom(self, classroom_id: UUID) -> list[Chapter]:
        result = await self._db.execute(
            select(ChapterModel)
            .where(ChapterModel.classroom_id == str(classroom_id))
            .order_by(ChapterModel.order_index.asc(), ChapterModel.created_at.asc())
        )
        return [_chapter_to_entity(m) for m in result.scalars().all()]

    async def update(self, chapter: Chapter) -> Chapter:
        result = await self._db.execute(
            select(ChapterModel).where(ChapterModel.id == str(chapter.id))
        )
        model = result.scalar_one()
        model.title = chapter.title
        model.description = chapter.description
        model.order_index = chapter.order_index
        model.is_published = chapter.is_published
        model.knowledge_base_id = (
            str(chapter.knowledge_base_id) if chapter.knowledge_base_id else None
        )
        await self._db.flush()
        await self._db.refresh(model)
        return _chapter_to_entity(model)

    async def delete(self, chapter_id: UUID) -> None:
        result = await self._db.execute(
            select(ChapterModel).where(ChapterModel.id == str(chapter_id))
        )
        model = result.scalar_one_or_none()
        if model:
            await self._db.delete(model)
            await self._db.flush()

    async def next_order_index(self, classroom_id: UUID) -> int:
        result = await self._db.execute(
            select(func.coalesce(func.max(ChapterModel.order_index), -1)).where(
                ChapterModel.classroom_id == str(classroom_id)
            )
        )
        return int(result.scalar_one()) + 1


class EnrollmentRepository(AbstractEnrollmentRepository):
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(self, enrollment: Enrollment) -> Enrollment:
        model = EnrollmentModel(
            id=str(enrollment.id),
            classroom_id=str(enrollment.classroom_id),
            student_id=str(enrollment.student_id),
            status=enrollment.status,
        )
        self._db.add(model)
        await self._db.flush()
        await self._db.refresh(model)
        return _enrollment_to_entity(model)

    async def get(self, classroom_id: UUID, student_id: UUID) -> Enrollment | None:
        result = await self._db.execute(
            select(EnrollmentModel).where(
                EnrollmentModel.classroom_id == str(classroom_id),
                EnrollmentModel.student_id == str(student_id),
            )
        )
        model = result.scalar_one_or_none()
        return _enrollment_to_entity(model) if model else None

    async def list_students(self, classroom_id: UUID, status: str = "active") -> list[User]:
        result = await self._db.execute(
            select(UserModel)
            .join(EnrollmentModel, EnrollmentModel.student_id == UserModel.id)
            .where(
                EnrollmentModel.classroom_id == str(classroom_id),
                EnrollmentModel.status == status,
            )
            .order_by(EnrollmentModel.joined_at.asc())
        )
        return [_user_to_entity(m) for m in result.scalars().all()]

    async def list_classrooms_for_student(self, student_id: UUID) -> list[Classroom]:
        result = await self._db.execute(
            select(ClassroomModel)
            .join(EnrollmentModel, EnrollmentModel.classroom_id == ClassroomModel.id)
            .where(
                EnrollmentModel.student_id == str(student_id),
                EnrollmentModel.status == "active",
                ClassroomModel.is_archived.is_(False),
                ClassroomModel.is_deleted.is_(False),
            )
            .order_by(EnrollmentModel.joined_at.desc())
        )
        return [_classroom_to_entity(m) for m in result.scalars().all()]

    async def is_enrolled(self, classroom_id: UUID, student_id: UUID) -> bool:
        result = await self._db.execute(
            select(func.count())
            .select_from(EnrollmentModel)
            .where(
                EnrollmentModel.classroom_id == str(classroom_id),
                EnrollmentModel.student_id == str(student_id),
                EnrollmentModel.status == "active",
            )
        )
        return int(result.scalar_one()) > 0

    async def set_status(self, classroom_id: UUID, student_id: UUID, status: str) -> None:
        result = await self._db.execute(
            select(EnrollmentModel).where(
                EnrollmentModel.classroom_id == str(classroom_id),
                EnrollmentModel.student_id == str(student_id),
            )
        )
        model = result.scalar_one_or_none()
        if model:
            model.status = status
            await self._db.flush()

    async def delete(self, classroom_id: UUID, student_id: UUID) -> None:
        result = await self._db.execute(
            select(EnrollmentModel).where(
                EnrollmentModel.classroom_id == str(classroom_id),
                EnrollmentModel.student_id == str(student_id),
            )
        )
        model = result.scalar_one_or_none()
        if model:
            await self._db.delete(model)
            await self._db.flush()
