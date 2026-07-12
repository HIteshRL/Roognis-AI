from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.entities.user import User


class AbstractUserRepository(ABC):
    @abstractmethod
    async def create(self, user: User) -> User: ...

    @abstractmethod
    async def get_by_id(self, user_id: UUID) -> User | None: ...

    @abstractmethod
    async def get_by_email(self, email: str) -> User | None: ...

    @abstractmethod
    async def get_by_username(self, username: str) -> User | None: ...

    @abstractmethod
    async def get_by_clerk_id(self, clerk_id: str) -> User | None: ...

    @abstractmethod
    async def update(self, user: User) -> User: ...

    @abstractmethod
    async def delete(self, user_id: UUID) -> None: ...

    @abstractmethod
    async def list(
        self,
        page: int = 1,
        limit: int = 50,
        role: str | None = None,
        search: str | None = None,
    ) -> tuple[list[User], int]: ...
