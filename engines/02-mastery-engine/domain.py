"""Minimal domain layer for the Mastery Engine."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel

BLOOM_GAINS: dict[str, int] = {
    "Remember": 3, "Understand": 5, "Apply": 8,
    "Analyze": 10, "Evaluate": 12, "Create": 15,
}


@dataclass
class ConceptNode:
    name: str
    id: UUID = field(default_factory=uuid4)
    subject: str | None = None
    grade: str | None = None
    chapter: str | None = None
    bloom_level: str = "Understand"
    difficulty: str = "medium"


@dataclass
class MasteryRecord:
    user_id: UUID
    concept_id: UUID
    concept_name: str
    id: UUID = field(default_factory=uuid4)
    score: float = 0.0
    interaction_count: int = 0
    last_updated: datetime = field(default_factory=lambda: datetime.now(UTC))

    def apply_interaction(self, bloom_level: str, has_misconception: bool) -> None:
        gain = BLOOM_GAINS.get(bloom_level, 5)
        penalty = 15 if has_misconception else 0
        session_score = max(0.0, gain - penalty)
        smoothed = 0.7 * self.score + 0.3 * (self.score + session_score)
        self.score = round(min(100.0, max(0.0, smoothed)), 2)
        self.interaction_count += 1
        self.last_updated = datetime.now(UTC)

    @property
    def label(self) -> str:
        if self.score >= 85: return "mastered"
        if self.score >= 60: return "developing"
        if self.score >= 30: return "emerging"
        return "not_started"


class ConceptExtractionResult(BaseModel):
    primary_concept: str
    secondary_concepts: list[str] = []
    skills: list[str] = []
    bloom_level: str = "Understand"
    difficulty: str = "medium"
    misconceptions: list[str] = []


class AbstractMasteryRepository(ABC):
    @abstractmethod
    async def get_or_create(self, user_id: UUID, concept_id: UUID, concept_name: str) -> MasteryRecord: ...
    @abstractmethod
    async def update(self, record: MasteryRecord) -> MasteryRecord: ...
    @abstractmethod
    async def list_by_user(self, user_id: UUID) -> list[MasteryRecord]: ...
    @abstractmethod
    async def average_score(self, user_id: UUID) -> float: ...


class AbstractConceptNodeRepository(ABC):
    @abstractmethod
    async def get_or_create(self, name: str, subject: str | None, grade: str | None, chapter: str | None) -> ConceptNode: ...
