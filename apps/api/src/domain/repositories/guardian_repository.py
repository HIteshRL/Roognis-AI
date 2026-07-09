from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.entities.guardian import GuardianLink


class AbstractGuardianRepository(ABC):
    @abstractmethod
    async def create(self, link: GuardianLink) -> GuardianLink: ...

    @abstractmethod
    async def get(self, parent_id: UUID, student_id: UUID) -> GuardianLink | None: ...

    @abstractmethod
    async def list_by_parent(self, parent_id: UUID) -> list[GuardianLink]: ...

    @abstractmethod
    async def list_by_student(self, student_id: UUID) -> list[GuardianLink]: ...

    @abstractmethod
    async def update(self, link: GuardianLink) -> GuardianLink: ...
