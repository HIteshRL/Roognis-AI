"""Minimal domain layer for the Learner Context Builder."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID, uuid4

BLOOM_LEVELS = ["Remember", "Understand", "Apply", "Analyze", "Evaluate", "Create"]


@dataclass
class BehavioralSignals:
    preferred_bloom_level: str | None = None
    struggle_bloom_level: str | None = None
    sessions_per_day: float = 0.0
    question_complexity_trend: str = "stable"
    total_sessions: int = 0
    total_misconceptions: int = 0
    engagement_streak: int = 0
    strengths: list[str] = field(default_factory=list)
    recent_topics: list[str] = field(default_factory=list)
    response_pattern: str = "unknown"
    last_computed: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "BehavioralSignals":
        if not data:
            return cls()
        return cls(**{k: data.get(k, v) for k, v in cls.__dataclass_fields__.items()
                      if k in data})


@dataclass
class StudentProfile:
    user_id: UUID
    id: UUID = field(default_factory=uuid4)
    grade: str | None = None
    subjects: list[str] = field(default_factory=list)
    current_chapter: str | None = None
    learning_velocity: float = 0.0
    confidence_score: float = 0.0
    behavioral_signals: BehavioralSignals = field(default_factory=BehavioralSignals)


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
    severity: str = "medium"
    reason: str = ""
    occurrence_count: int = 1
    is_resolved: bool = False


class AbstractStudentProfileRepository(ABC):
    @abstractmethod
    async def get_by_user_id(self, user_id: UUID) -> StudentProfile | None: ...


class AbstractMasteryRepository(ABC):
    @abstractmethod
    async def list_by_user(self, user_id: UUID) -> list[MasteryRecord]: ...


class AbstractLearningGapRepository(ABC):
    @abstractmethod
    async def list_by_user(self, user_id: UUID, include_resolved: bool = False) -> list[LearningGap]: ...
