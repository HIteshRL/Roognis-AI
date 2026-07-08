from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.entities.school import (
    Classroom,
    Enrollment,
    School,
    SchoolMember,
    SyllabusItem,
)


class AbstractSchoolRepository(ABC):
    @abstractmethod
    async def create(self, school: School) -> School: ...

    @abstractmethod
    async def get_by_id(self, school_id: UUID) -> School | None: ...

    @abstractmethod
    async def get_by_slug(self, slug: str) -> School | None: ...

    @abstractmethod
    async def list_for_member(self, user_id: UUID) -> list[School]: ...


class AbstractSchoolMemberRepository(ABC):
    @abstractmethod
    async def create(self, member: SchoolMember) -> SchoolMember: ...

    @abstractmethod
    async def get(self, school_id: UUID, user_id: UUID) -> SchoolMember | None: ...

    @abstractmethod
    async def list_by_school(self, school_id: UUID) -> list[SchoolMember]: ...


class AbstractClassroomRepository(ABC):
    @abstractmethod
    async def create(self, classroom: Classroom) -> Classroom: ...

    @abstractmethod
    async def get_by_id(self, classroom_id: UUID) -> Classroom | None: ...

    @abstractmethod
    async def get_by_join_code(self, join_code: str) -> Classroom | None: ...

    @abstractmethod
    async def list_by_teacher(self, teacher_id: UUID) -> list[Classroom]: ...

    @abstractmethod
    async def list_by_school(self, school_id: UUID) -> list[Classroom]: ...

    @abstractmethod
    async def list_by_ids(self, classroom_ids: list[UUID]) -> list[Classroom]: ...

    @abstractmethod
    async def update(self, classroom: Classroom) -> Classroom: ...

    @abstractmethod
    async def delete(self, classroom_id: UUID) -> None: ...


class AbstractEnrollmentRepository(ABC):
    @abstractmethod
    async def create(self, enrollment: Enrollment) -> Enrollment: ...

    @abstractmethod
    async def get(self, classroom_id: UUID, student_id: UUID) -> Enrollment | None: ...

    @abstractmethod
    async def list_by_classroom(self, classroom_id: UUID) -> list[Enrollment]: ...

    @abstractmethod
    async def list_by_student(self, student_id: UUID) -> list[Enrollment]: ...

    @abstractmethod
    async def update(self, enrollment: Enrollment) -> Enrollment: ...

    @abstractmethod
    async def count_by_classroom(self, classroom_id: UUID) -> int: ...


class AbstractSyllabusRepository(ABC):
    @abstractmethod
    async def create(self, item: SyllabusItem) -> SyllabusItem: ...

    @abstractmethod
    async def get_by_id(self, item_id: UUID) -> SyllabusItem | None: ...

    @abstractmethod
    async def list_by_classroom(
        self, classroom_id: UUID, published_only: bool = False
    ) -> list[SyllabusItem]: ...

    @abstractmethod
    async def update(self, item: SyllabusItem) -> SyllabusItem: ...

    @abstractmethod
    async def delete(self, item_id: UUID) -> None: ...
