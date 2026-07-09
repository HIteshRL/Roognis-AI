from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.entities.media_job import MediaJob


class AbstractMediaJobRepository(ABC):
    @abstractmethod
    async def create(self, job: MediaJob) -> MediaJob: ...

    @abstractmethod
    async def get_by_id(self, job_id: UUID) -> MediaJob | None: ...

    @abstractmethod
    async def update(self, job: MediaJob) -> MediaJob: ...

    @abstractmethod
    async def list_by_message(self, message_id: UUID) -> list[MediaJob]: ...
