"""Minimal domain layer for the Learning Gap Detector."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel


@dataclass
class ConceptNode:
    name: str
    id: UUID = field(default_factory=uuid4)
    subject: str | None = None
    grade: str | None = None
    chapter: str | None = None


@dataclass
class LearningGap:
    user_id: UUID
    concept_id: UUID
    concept_name: str
    id: UUID = field(default_factory=uuid4)
    severity: str = "medium"
    reason: str = ""
    confidence: str = "medium"
    occurrence_count: int = 1
    is_resolved: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def increment(self) -> None:
        self.occurrence_count += 1
        self.updated_at = datetime.now(UTC)
        if self.occurrence_count >= 5:
            self.severity, self.confidence = "critical", "high"
        elif self.occurrence_count >= 3:
            self.severity, self.confidence = "high", "high"
        elif self.occurrence_count >= 2:
            self.severity, self.confidence = "medium", "medium"

    def resolve(self) -> None:
        self.is_resolved = True
        self.updated_at = datetime.now(UTC)


class ConceptExtractionResult(BaseModel):
    primary_concept: str
    secondary_concepts: list[str] = []
    bloom_level: str = "Understand"
    difficulty: str = "medium"
    misconceptions: list[str] = []


class AbstractLearningGapRepository(ABC):
    @abstractmethod
    async def get_or_create(self, user_id: UUID, concept_id: UUID, concept_name: str, reason: str) -> LearningGap: ...
    @abstractmethod
    async def update(self, gap: LearningGap) -> LearningGap: ...
    @abstractmethod
    async def list_by_user(self, user_id: UUID, include_resolved: bool = False) -> list[LearningGap]: ...
    @abstractmethod
    async def resolve(self, gap_id: UUID) -> None: ...


class AbstractConceptNodeRepository(ABC):
    @abstractmethod
    async def get_or_create(self, name: str, subject: str | None, grade: str | None, chapter: str | None) -> ConceptNode: ...
