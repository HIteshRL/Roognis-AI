"""Minimal domain layer for the Concept Memory Engine."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel

BLOOM_LEVELS = ["Remember", "Understand", "Apply", "Analyze", "Evaluate", "Create"]


@dataclass
class ConceptNode:
    name: str
    id: UUID = field(default_factory=uuid4)
    subject: str | None = None
    grade: str | None = None
    chapter: str | None = None


@dataclass
class ConceptMemory:
    user_id: UUID
    concept_id: UUID
    concept_name: str
    id: UUID = field(default_factory=uuid4)
    times_taught: int = 0
    successful_approaches: int = 0
    failed_approaches: int = 0
    last_approach: str | None = None
    teaching_notes: list[str] = field(default_factory=list)
    last_taught: datetime = field(default_factory=lambda: datetime.now(UTC))
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def record_interaction(self, approach: str, had_misconception: bool, note: str | None = None) -> None:
        self.times_taught += 1
        self.last_approach = approach
        self.last_taught = datetime.now(UTC)
        self.updated_at = datetime.now(UTC)
        if had_misconception:
            self.failed_approaches += 1
            if note and note not in self.teaching_notes:
                self.teaching_notes = (self.teaching_notes + [note])[-5:]
        else:
            self.successful_approaches += 1

    @property
    def success_rate(self) -> float:
        total = self.successful_approaches + self.failed_approaches
        return round(self.successful_approaches / total, 2) if total > 0 else 0.0

    @property
    def needs_different_approach(self) -> bool:
        return self.times_taught >= 3 and self.success_rate < 0.5


class ConceptExtractionResult(BaseModel):
    primary_concept: str
    secondary_concepts: list[str] = []
    bloom_level: str = "Understand"
    difficulty: str = "medium"
    misconceptions: list[str] = []


class AbstractConceptMemoryRepository(ABC):
    @abstractmethod
    async def get_or_create(self, user_id: UUID, concept_id: UUID, concept_name: str) -> ConceptMemory: ...
    @abstractmethod
    async def update(self, memory: ConceptMemory) -> ConceptMemory: ...
    @abstractmethod
    async def list_by_user(self, user_id: UUID) -> list[ConceptMemory]: ...


class AbstractConceptNodeRepository(ABC):
    @abstractmethod
    async def get_or_create(self, name: str, subject: str | None, grade: str | None, chapter: str | None) -> ConceptNode: ...
