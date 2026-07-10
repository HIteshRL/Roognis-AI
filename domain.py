"""Minimal domain layer for the Learning Velocity Engine."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4

BLOOM_GAINS: dict[str, int] = {
    "Remember": 3, "Understand": 5, "Apply": 8,
    "Analyze": 10, "Evaluate": 12, "Create": 15,
}


@dataclass
class LearningSession:
    user_id: UUID
    question: str
    ai_response: str
    id: UUID = field(default_factory=uuid4)
    bloom_level: str = "Understand"
    misconceptions: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class MasteryRecord:
    user_id: UUID
    concept_id: UUID
    concept_name: str
    id: UUID = field(default_factory=uuid4)
    score: float = 0.0
    last_updated: datetime = field(default_factory=lambda: datetime.now(UTC))


class AbstractLearningSessionRepository(ABC):
    @abstractmethod
    async def list_since(self, user_id: UUID, since: datetime) -> list[LearningSession]: ...


class AbstractMasteryRepository(ABC):
    @abstractmethod
    async def list_by_user(self, user_id: UUID) -> list[MasteryRecord]: ...
