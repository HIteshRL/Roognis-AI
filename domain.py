"""Minimal domain layer for the Learning Path Engine."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from uuid import UUID, uuid4

from pydantic import BaseModel


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
class StudentProfile:
    user_id: UUID
    id: UUID = field(default_factory=uuid4)
    grade: str | None = None
    subjects: list[str] = field(default_factory=list)


class RecommendationResponse(BaseModel):
    concept_id: UUID
    concept_name: str
    subject: str | None = None
    chapter: str | None = None
    reason: str = ""
    readiness_score: float = 0.0


class AbstractMasteryRepository(ABC):
    @abstractmethod
    async def list_by_user(self, user_id: UUID) -> list: ...


class AbstractStudentProfileRepository(ABC):
    @abstractmethod
    async def get_by_user_id(self, user_id: UUID) -> StudentProfile | None: ...


class AbstractKnowledgeGraph(ABC):
    """Interface for the knowledge graph — implement against your graph storage."""
    @abstractmethod
    async def get_all_prerequisites(self, concept_id: UUID) -> list[ConceptNode]: ...
    @abstractmethod
    async def learning_order(self, concept_ids: list[UUID]) -> list[UUID]: ...
    @abstractmethod
    async def list_by_subject(self, subject: str, grade: str) -> list[ConceptNode]: ...
    @abstractmethod
    async def readiness_for(self, concept_id: UUID, mastery_map: dict[UUID, float]) -> float: ...
