"""Abstract repositories for the Learner Intelligence questioning subsystem."""
from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID

from src.domain.entities.question import (
    GeneratedQuestion,
    LearnerEvidence,
    LearnerPreference,
    RecallSchedule,
)


class AbstractEvidenceRepository(ABC):
    """Append-only. Evidence is never updated or deleted — it is a fact log."""

    @abstractmethod
    async def add(self, evidence: LearnerEvidence) -> LearnerEvidence: ...

    @abstractmethod
    async def list_by_user(self, user_id: UUID, limit: int = 100) -> list[LearnerEvidence]: ...

    @abstractmethod
    async def list_by_concept(
        self, user_id: UUID, concept_id: UUID, limit: int = 50
    ) -> list[LearnerEvidence]: ...

    @abstractmethod
    async def count_by_concept(self, user_id: UUID, concept_id: UUID) -> int: ...


class AbstractLearnerQuestionRepository(ABC):
    @abstractmethod
    async def create(self, question: GeneratedQuestion) -> GeneratedQuestion: ...

    @abstractmethod
    async def update(self, question: GeneratedQuestion) -> GeneratedQuestion: ...

    @abstractmethod
    async def get_by_id(self, question_id: UUID) -> GeneratedQuestion | None: ...

    @abstractmethod
    async def list_by_user(
        self, user_id: UUID, status: str | None = None, limit: int = 20
    ) -> list[GeneratedQuestion]: ...

    @abstractmethod
    async def next_pending(self, user_id: UUID) -> GeneratedQuestion | None: ...


class AbstractRecallScheduleRepository(ABC):
    @abstractmethod
    async def get_or_create(
        self, user_id: UUID, concept_id: UUID, concept_name: str
    ) -> RecallSchedule: ...

    @abstractmethod
    async def update(self, schedule: RecallSchedule) -> RecallSchedule: ...

    @abstractmethod
    async def get_by_concept(self, user_id: UUID, concept_id: UUID) -> RecallSchedule | None: ...

    @abstractmethod
    async def list_by_user(self, user_id: UUID) -> list[RecallSchedule]: ...

    @abstractmethod
    async def list_due(self, user_id: UUID, now: datetime) -> list[RecallSchedule]: ...


class AbstractLearnerPreferenceRepository(ABC):
    @abstractmethod
    async def get_or_create(self, user_id: UUID, dimension: str) -> LearnerPreference: ...

    @abstractmethod
    async def update(self, preference: LearnerPreference) -> LearnerPreference: ...

    @abstractmethod
    async def list_by_user(self, user_id: UUID) -> list[LearnerPreference]: ...
