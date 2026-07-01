from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4

# Bloom's taxonomy levels in ascending cognitive order
BLOOM_LEVELS = ["Remember", "Understand", "Apply", "Analyze", "Evaluate", "Create"]

# Points awarded per Bloom level on a correct interaction
BLOOM_GAINS = {
    "Remember": 3,
    "Understand": 5,
    "Apply": 8,
    "Analyze": 10,
    "Evaluate": 12,
    "Create": 15,
}


@dataclass
class StudentProfile:
    user_id: UUID
    id: UUID = field(default_factory=uuid4)
    institution: str | None = None
    grade: str | None = None
    subjects: list[str] = field(default_factory=list)
    current_chapter: str | None = None
    learning_velocity: float = 0.0   # avg mastery-points gained per day
    confidence_score: float = 0.0    # 0–1, derived from recent mastery
    last_active: datetime = field(default_factory=lambda: datetime.now(UTC))
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def touch(self) -> None:
        self.last_active = datetime.now(UTC)
        self.updated_at = datetime.now(UTC)

    def update_confidence(self, avg_mastery: float) -> None:
        self.confidence_score = round(avg_mastery / 100.0, 3)
        self.updated_at = datetime.now(UTC)


@dataclass
class LearningSession:
    user_id: UUID
    question: str
    ai_response: str
    id: UUID = field(default_factory=uuid4)
    conversation_id: UUID | None = None
    subject: str | None = None
    chapter: str | None = None
    grade: str | None = None
    retrieved_context: str | None = None
    primary_concept: str | None = None
    concepts_discussed: list[str] = field(default_factory=list)
    skills: list[str] = field(default_factory=list)
    bloom_level: str = "Understand"
    difficulty_level: str = "medium"   # low | medium | high
    misconceptions: list[str] = field(default_factory=list)
    token_count: int = 0
    duration_ms: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class ConceptNode:
    name: str
    id: UUID = field(default_factory=uuid4)
    subject: str | None = None
    grade: str | None = None
    chapter: str | None = None
    description: str | None = None
    bloom_level: str = "Understand"
    difficulty: str = "medium"
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class ConceptEdge:
    """source_id is a prerequisite of target_id."""
    source_id: UUID
    target_id: UUID
    id: UUID = field(default_factory=uuid4)
    weight: float = 1.0
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class MasteryRecord:
    user_id: UUID
    concept_id: UUID
    concept_name: str
    id: UUID = field(default_factory=uuid4)
    score: float = 0.0          # 0–100
    interaction_count: int = 0
    last_updated: datetime = field(default_factory=lambda: datetime.now(UTC))
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def apply_interaction(self, bloom_level: str, has_misconception: bool) -> None:
        """
        Update score using a smoothed gain model.
        Higher Bloom levels yield more gain; misconceptions apply a penalty.
        Uses EMA-style smoothing: new = 0.7*old + 0.3*session_score to prevent
        single-session spikes to 100.
        """
        gain = BLOOM_GAINS.get(bloom_level, 5)
        penalty = 15 if has_misconception else 0
        session_score = max(0.0, gain - penalty)

        # Smooth: existing score has 70% weight, new interaction 30%
        smoothed = 0.7 * self.score + 0.3 * (self.score + session_score)
        self.score = round(min(100.0, max(0.0, smoothed)), 2)
        self.interaction_count += 1
        self.last_updated = datetime.now(UTC)

    @property
    def label(self) -> str:
        if self.score >= 85:
            return "mastered"
        if self.score >= 60:
            return "developing"
        if self.score >= 30:
            return "emerging"
        return "not_started"


@dataclass
class LearningGap:
    user_id: UUID
    concept_id: UUID
    concept_name: str
    id: UUID = field(default_factory=uuid4)
    severity: str = "medium"      # low | medium | high | critical
    reason: str = ""
    confidence: str = "medium"    # low | medium | high
    occurrence_count: int = 1
    is_resolved: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def increment(self) -> None:
        self.occurrence_count += 1
        self.updated_at = datetime.now(UTC)
        if self.occurrence_count >= 5:
            self.severity = "critical"
            self.confidence = "high"
        elif self.occurrence_count >= 3:
            self.severity = "high"
            self.confidence = "high"
        elif self.occurrence_count >= 2:
            self.severity = "medium"
            self.confidence = "medium"

    def resolve(self) -> None:
        self.is_resolved = True
        self.updated_at = datetime.now(UTC)
