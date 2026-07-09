from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.school import (
    Classroom,
    Enrollment,
    School,
    SchoolMember,
    SyllabusItem,
)
from src.domain.repositories.school_repository import (
    AbstractClassroomRepository,
    AbstractEnrollmentRepository,
    AbstractSchoolMemberRepository,
    AbstractSchoolRepository,
    AbstractSyllabusRepository,
)
from src.infrastructure.database.models.school import (
    ClassroomModel,
    EnrollmentModel,
    SchoolMemberModel,
    SchoolModel,
    SyllabusItemModel,
)

# ── Mappers ──────────────────────────────────────────────────────────────────


def _uid(value: str | None) -> UUID | None:
    return UUID(value) if value else None


def _to_school(m: SchoolModel) -> School:
    s = School.__new__(School)
    s.id = UUID(m.id)
    s.name = m.name
    s.slug = m.slug
    s.address = m.address
    s.created_by = _uid(m.created_by)
    s.is_active = m.is_active
    s.created_at = m.created_at
    s.updated_at = m.updated_at
    return s


def _to_member(m: SchoolMemberModel) -> SchoolMember:
    x = SchoolMember.__new__(SchoolMember)
    x.id = UUID(m.id)
    x.school_id = UUID(m.school_id)
    x.user_id = UUID(m.user_id)
    x.role = m.role
    x.status = m.status
    x.created_at = m.created_at
    x.updated_at = m.updated_at
    return x


def _to_classroom(m: ClassroomModel) -> Classroom:
    c = Classroom.__new__(Classroom)
    c.id = UUID(m.id)
    c.school_id = UUID(m.school_id)
    c.name = m.name
    c.subject = m.subject
    c.grade = m.grade
    c.teacher_id = _uid(m.teacher_id)
    c.join_code = m.join_code
    c.description = m.description
    c.is_active = m.is_active
    c.knowledge_base_id = _uid(m.knowledge_base_id)
    c.created_at = m.created_at
    c.updated_at = m.updated_at
    return c


def _to_enrollment(m: EnrollmentModel) -> Enrollment:
    e = Enrollment.__new__(Enrollment)
    e.id = UUID(m.id)
    e.classroom_id = UUID(m.classroom_id)
    e.student_id = UUID(m.student_id)
    e.status = m.status
    e.created_at = m.created_at
    e.updated_at = m.updated_at
    return e


def _to_syllabus(m: SyllabusItemModel) -> SyllabusItem:
    i = SyllabusItem.__new__(SyllabusItem)
    i.id = UUID(m.id)
    i.classroom_id = UUID(m.classroom_id)
    i.subject = m.subject
    i.chapter = m.chapter
    i.topic = m.topic
    i.description = m.description
    i.order_index = m.order_index
    i.knowledge_base_id = _uid(m.knowledge_base_id)
    i.is_published = m.is_published
    i.created_at = m.created_at
    i.updated_at = m.updated_at
    return i


# ── Repositories ─────────────────────────────────────────────────────────────


class SchoolRepository(AbstractSchoolRepository):
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(self, school: School) -> School:
        m = SchoolModel(
            id=str(school.id),
            name=school.name,
            slug=school.slug,
            address=school.address,
            created_by=str(school.created_by) if school.created_by else None,
            is_active=school.is_active,
        )
        self._db.add(m)
        await self._db.flush()
        await self._db.refresh(m)
        return _to_school(m)

    async def get_by_id(self, school_id: UUID) -> School | None:
        result = await self._db.execute(
            select(SchoolModel).where(SchoolModel.id == str(school_id))
        )
        m = result.scalar_one_or_none()
        return _to_school(m) if m else None

    async def get_by_slug(self, slug: str) -> School | None:
        result = await self._db.execute(
            select(SchoolModel).where(SchoolModel.slug == slug)
        )
        m = result.scalar_one_or_none()
        return _to_school(m) if m else None

    async def list_for_member(self, user_id: UUID) -> list[School]:
        stmt = (
            select(SchoolModel)
            .join(SchoolMemberModel, SchoolMemberModel.school_id == SchoolModel.id)
            .where(SchoolMemberModel.user_id == str(user_id))
            .order_by(SchoolModel.created_at.desc())
        )
        result = await self._db.execute(stmt)
        return [_to_school(m) for m in result.scalars().all()]


class SchoolMemberRepository(AbstractSchoolMemberRepository):
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(self, member: SchoolMember) -> SchoolMember:
        m = SchoolMemberModel(
            id=str(member.id),
            school_id=str(member.school_id),
            user_id=str(member.user_id),
            role=member.role,
            status=member.status,
        )
        self._db.add(m)
        await self._db.flush()
        await self._db.refresh(m)
        return _to_member(m)

    async def get(self, school_id: UUID, user_id: UUID) -> SchoolMember | None:
        result = await self._db.execute(
            select(SchoolMemberModel).where(
                SchoolMemberModel.school_id == str(school_id),
                SchoolMemberModel.user_id == str(user_id),
            )
        )
        m = result.scalar_one_or_none()
        return _to_member(m) if m else None

    async def list_by_school(self, school_id: UUID) -> list[SchoolMember]:
        result = await self._db.execute(
            select(SchoolMemberModel).where(
                SchoolMemberModel.school_id == str(school_id)
            )
        )
        return [_to_member(m) for m in result.scalars().all()]


class ClassroomRepository(AbstractClassroomRepository):
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(self, classroom: Classroom) -> Classroom:
        m = ClassroomModel(
            id=str(classroom.id),
            school_id=str(classroom.school_id),
            name=classroom.name,
            subject=classroom.subject,
            grade=classroom.grade,
            teacher_id=str(classroom.teacher_id) if classroom.teacher_id else None,
            join_code=classroom.join_code,
            description=classroom.description,
            is_active=classroom.is_active,
            knowledge_base_id=(
                str(classroom.knowledge_base_id) if classroom.knowledge_base_id else None
            ),
        )
        self._db.add(m)
        await self._db.flush()
        await self._db.refresh(m)
        return _to_classroom(m)

    async def get_by_id(self, classroom_id: UUID) -> Classroom | None:
        result = await self._db.execute(
            select(ClassroomModel).where(ClassroomModel.id == str(classroom_id))
        )
        m = result.scalar_one_or_none()
        return _to_classroom(m) if m else None

    async def get_by_join_code(self, join_code: str) -> Classroom | None:
        result = await self._db.execute(
            select(ClassroomModel).where(ClassroomModel.join_code == join_code)
        )
        m = result.scalar_one_or_none()
        return _to_classroom(m) if m else None

    async def list_by_teacher(self, teacher_id: UUID) -> list[Classroom]:
        result = await self._db.execute(
            select(ClassroomModel)
            .where(ClassroomModel.teacher_id == str(teacher_id))
            .order_by(ClassroomModel.created_at.desc())
        )
        return [_to_classroom(m) for m in result.scalars().all()]

    async def list_by_school(self, school_id: UUID) -> list[Classroom]:
        result = await self._db.execute(
            select(ClassroomModel)
            .where(ClassroomModel.school_id == str(school_id))
            .order_by(ClassroomModel.created_at.desc())
        )
        return [_to_classroom(m) for m in result.scalars().all()]

    async def list_by_ids(self, classroom_ids: list[UUID]) -> list[Classroom]:
        if not classroom_ids:
            return []
        ids = [str(c) for c in classroom_ids]
        result = await self._db.execute(
            select(ClassroomModel).where(ClassroomModel.id.in_(ids))
        )
        return [_to_classroom(m) for m in result.scalars().all()]

    async def update(self, classroom: Classroom) -> Classroom:
        result = await self._db.execute(
            select(ClassroomModel).where(ClassroomModel.id == str(classroom.id))
        )
        m = result.scalar_one()
        m.name = classroom.name
        m.subject = classroom.subject
        m.grade = classroom.grade
        m.teacher_id = str(classroom.teacher_id) if classroom.teacher_id else None
        m.description = classroom.description
        m.is_active = classroom.is_active
        m.knowledge_base_id = (
            str(classroom.knowledge_base_id) if classroom.knowledge_base_id else None
        )
        await self._db.flush()
        await self._db.refresh(m)
        return _to_classroom(m)

    async def delete(self, classroom_id: UUID) -> None:
        result = await self._db.execute(
            select(ClassroomModel).where(ClassroomModel.id == str(classroom_id))
        )
        m = result.scalar_one_or_none()
        if m:
            await self._db.delete(m)
            await self._db.flush()


class EnrollmentRepository(AbstractEnrollmentRepository):
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(self, enrollment: Enrollment) -> Enrollment:
        m = EnrollmentModel(
            id=str(enrollment.id),
            classroom_id=str(enrollment.classroom_id),
            student_id=str(enrollment.student_id),
            status=enrollment.status,
        )
        self._db.add(m)
        await self._db.flush()
        await self._db.refresh(m)
        return _to_enrollment(m)

    async def get(self, classroom_id: UUID, student_id: UUID) -> Enrollment | None:
        result = await self._db.execute(
            select(EnrollmentModel).where(
                EnrollmentModel.classroom_id == str(classroom_id),
                EnrollmentModel.student_id == str(student_id),
            )
        )
        m = result.scalar_one_or_none()
        return _to_enrollment(m) if m else None

    async def list_by_classroom(self, classroom_id: UUID) -> list[Enrollment]:
        result = await self._db.execute(
            select(EnrollmentModel)
            .where(EnrollmentModel.classroom_id == str(classroom_id))
            .order_by(EnrollmentModel.created_at.desc())
        )
        return [_to_enrollment(m) for m in result.scalars().all()]

    async def list_by_student(self, student_id: UUID) -> list[Enrollment]:
        result = await self._db.execute(
            select(EnrollmentModel)
            .where(
                EnrollmentModel.student_id == str(student_id),
                EnrollmentModel.status == "active",
            )
            .order_by(EnrollmentModel.created_at.desc())
        )
        return [_to_enrollment(m) for m in result.scalars().all()]

    async def update(self, enrollment: Enrollment) -> Enrollment:
        result = await self._db.execute(
            select(EnrollmentModel).where(EnrollmentModel.id == str(enrollment.id))
        )
        m = result.scalar_one()
        m.status = enrollment.status
        await self._db.flush()
        await self._db.refresh(m)
        return _to_enrollment(m)

    async def count_by_classroom(self, classroom_id: UUID) -> int:
        result = await self._db.execute(
            select(func.count(EnrollmentModel.id)).where(
                EnrollmentModel.classroom_id == str(classroom_id),
                EnrollmentModel.status == "active",
            )
        )
        return result.scalar_one()


class SyllabusRepository(AbstractSyllabusRepository):
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(self, item: SyllabusItem) -> SyllabusItem:
        m = SyllabusItemModel(
            id=str(item.id),
            classroom_id=str(item.classroom_id),
            subject=item.subject,
            chapter=item.chapter,
            topic=item.topic,
            description=item.description,
            order_index=item.order_index,
            knowledge_base_id=(
                str(item.knowledge_base_id) if item.knowledge_base_id else None
            ),
            is_published=item.is_published,
        )
        self._db.add(m)
        await self._db.flush()
        await self._db.refresh(m)
        return _to_syllabus(m)

    async def get_by_id(self, item_id: UUID) -> SyllabusItem | None:
        result = await self._db.execute(
            select(SyllabusItemModel).where(SyllabusItemModel.id == str(item_id))
        )
        m = result.scalar_one_or_none()
        return _to_syllabus(m) if m else None

    async def list_by_classroom(
        self, classroom_id: UUID, published_only: bool = False
    ) -> list[SyllabusItem]:
        stmt = (
            select(SyllabusItemModel)
            .where(SyllabusItemModel.classroom_id == str(classroom_id))
            .order_by(SyllabusItemModel.order_index, SyllabusItemModel.created_at)
        )
        if published_only:
            stmt = stmt.where(SyllabusItemModel.is_published.is_(True))
        result = await self._db.execute(stmt)
        return [_to_syllabus(m) for m in result.scalars().all()]

    async def update(self, item: SyllabusItem) -> SyllabusItem:
        result = await self._db.execute(
            select(SyllabusItemModel).where(SyllabusItemModel.id == str(item.id))
        )
        m = result.scalar_one()
        m.subject = item.subject
        m.chapter = item.chapter
        m.topic = item.topic
        m.description = item.description
        m.order_index = item.order_index
        m.knowledge_base_id = (
            str(item.knowledge_base_id) if item.knowledge_base_id else None
        )
        m.is_published = item.is_published
        await self._db.flush()
        await self._db.refresh(m)
        return _to_syllabus(m)

    async def delete(self, item_id: UUID) -> None:
        result = await self._db.execute(
            select(SyllabusItemModel).where(SyllabusItemModel.id == str(item_id))
        )
        m = result.scalar_one_or_none()
        if m:
            await self._db.delete(m)
            await self._db.flush()
