from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.entities.psychometric import PsychometricProfile, PsychometricResponse


class AbstractPsychometricRepository(ABC):
    @abstractmethod
    async def get_profile(self, user_id: UUID) -> PsychometricProfile | None:
        """Read the stored psychometric_profile JSONB. None if the student
        profile row does not exist yet."""
        ...

    @abstractmethod
    async def save_profile(self, user_id: UUID, profile: PsychometricProfile) -> None:
        """Persist the computed profile onto the student_profiles row."""
        ...

    @abstractmethod
    async def upsert_response(self, response: PsychometricResponse) -> PsychometricResponse:
        """Store (or replace) a single survey answer, keyed by (user, question)."""
        ...

    @abstractmethod
    async def list_responses(self, user_id: UUID) -> list[PsychometricResponse]:
        ...

    @abstractmethod
    async def answered_keys(self, user_id: UUID) -> set[str]:
        ...
