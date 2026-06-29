from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.entities.profile import Profile, Settings


class AbstractProfileRepository(ABC):
    @abstractmethod
    async def create(self, profile: Profile) -> Profile: ...

    @abstractmethod
    async def get_by_user_id(self, user_id: UUID) -> Profile | None: ...

    @abstractmethod
    async def update(self, profile: Profile) -> Profile: ...


class AbstractSettingsRepository(ABC):
    @abstractmethod
    async def create(self, settings: Settings) -> Settings: ...

    @abstractmethod
    async def get_by_user_id(self, user_id: UUID) -> Settings | None: ...

    @abstractmethod
    async def update(self, settings: Settings) -> Settings: ...
