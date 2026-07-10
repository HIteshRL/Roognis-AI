"""Minimal domain layer for the Learner Behavior Analyzer."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4
from typing import Any

BLOOM_LEVELS = ["Remember", "Understand", "Apply", "Analyze", "Evaluate", "Create"]


@dataclass
class BehavioralSignals:
    preferred_bloom_level: str | None = None
    struggle_bloom_level: str | None = None
    avg_session_duration_ms: int = 0
    sessions_per_day: float = 0.0
    question_complexity_trend: str = "stable"
    dominant_subject: str | None = None
    total_sessions: int = 0
    total_misconceptions: int = 0
    engagement_streak: int = 0
    strengths: list[str] = field(default_factory=list)
    recent_topics: list[str] = field(default_factory=list)
    response_pattern: str = "unknown"
    last_computed: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in self.__dict__.items()}

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "BehavioralSignals":
        if not data:
            return cls()
        return cls(**{k: data.get(k, v) for k, v in cls.__dataclass_fields__.items()})


@dataclass
class LearningSession:
    user_id: UUID
    question: str
    ai_response: str
    id: UUID = field(default_factory=uuid4)
    subject: str | None = None
    bloom_level: str = "Understand"
    misconceptions: list[str] = field(default_factory=list)
    primary_concept: str | None = None
    duration_ms: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class MasteryRecord:
    user_id: UUID
    concept_id: UUID
    concept_name: str
    id: UUID = field(default_factory=uuid4)
    score: float = 0.0


@dataclass
class LearningGap:
    user_id: UUID
    concept_id: UUID
    concept_name: str
    id: UUID = field(default_factory=uuid4)
    is_resolved: bool = False


class AbstractLearningSessionRepository(ABC):
    @abstractmethod
    async def list_since(self, user_id: UUID, since: datetime) -> list[LearningSession]: ...
    @abstractmethod
    async def count_by_user(self, user_id: UUID) -> int: ...


class AbstractMasteryRepository(ABC):
    @abstractmethod
    async def list_by_user(self, user_id: UUID) -> list[MasteryRecord]: ...


class AbstractLearningGapRepository(ABC):
    @abstractmethod
    async def list_by_user(self, user_id: UUID, include_resolved: bool = False) -> list[LearningGap]: ...
