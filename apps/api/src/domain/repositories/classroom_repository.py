from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.entities.classroom import Chapter, Classroom, Enrollment
from src.domain.entities.user import User


class AbstractClassroomRepository(ABC):
    @abstractmethod
    async def create(self, classroom: Classroom) -> Classroom: ...

    @abstractmethod
    async def get_by_id(self, classroom_id: UUID) -> Classroom | None: ...

    @abstractmethod
    async def get_by_join_code(self, join_code: str) -> Classroom | None: ...

    @abstractmethod
    async def list_by_teacher(self, teacher_id: UUID, include_archived: bool = False) -> list[Classroom]: ...

    @abstractmethod
    async def update(self, classroom: Classroom) -> Classroom: ...

    @abstractmethod
    async def delete(self, classroom_id: UUID) -> None: ...

    @abstractmethod
    async def count_students(self, classroom_id: UUID) -> int: ...

    @abstractmethod
    async def count_chapters(self, classroom_id: UUID) -> int: ...


class AbstractChapterRepository(ABC):
    @abstractmethod
    async def create(self, chapter: Chapter) -> Chapter: ...

    @abstractmethod
    async def get_by_id(self, chapter_id: UUID) -> Chapter | None: ...

    @abstractmethod
    async def list_by_classroom(self, classroom_id: UUID) -> list[Chapter]: ...

    @abstractmethod
    async def update(self, chapter: Chapter) -> Chapter: ...

    @abstractmethod
    async def delete(self, chapter_id: UUID) -> None: ...

    @abstractmethod
    async def next_order_index(self, classroom_id: UUID) -> int: ...


class AbstractEnrollmentRepository(ABC):
    @abstractmethod
    async def create(self, enrollment: Enrollment) -> Enrollment: ...

    @abstractmethod
    async def get(self, classroom_id: UUID, student_id: UUID) -> Enrollment | None: ...

    @abstractmethod
    async def list_students(self, classroom_id: UUID) -> list[User]: ...

    @abstractmethod
    async def list_classrooms_for_student(self, student_id: UUID) -> list[Classroom]: ...

    @abstractmethod
    async def is_enrolled(self, classroom_id: UUID, student_id: UUID) -> bool: ...

    @abstractmethod
    async def delete(self, classroom_id: UUID, student_id: UUID) -> None: ...
