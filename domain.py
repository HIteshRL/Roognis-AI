"""Minimal domain layer for the Skill Graph Engine."""
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4

BLOOM_LEVELS = ["Remember", "Understand", "Apply", "Analyze", "Evaluate", "Create"]


@dataclass
class LearningSession:
    user_id: UUID
    question: str
    ai_response: str
    id: UUID = field(default_factory=uuid4)
    bloom_level: str = "Understand"
    primary_concept: str | None = None
    concepts_discussed: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class MasteryRecord:
    user_id: UUID
    concept_id: UUID
    concept_name: str
    id: UUID = field(default_factory=uuid4)
    score: float = 0.0
