from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4


@dataclass
class Quiz:
    user_id: UUID
    title: str
    id: UUID = field(default_factory=uuid4)
    subject: str | None = None
    chapter: str | None = None
    difficulty: str = "medium"
    question_count: int = 0
    total_attempts: int = 0
    best_score: float = 0.0
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class QuizQuestion:
    quiz_id: UUID
    concept_name: str
    question_text: str
    id: UUID = field(default_factory=uuid4)
    concept_id: UUID | None = None
    question_type: str = "mcq"
    options: list[str] = field(default_factory=list)
    correct_answer: str = ""
    explanation: str = ""
    bloom_level: str = "Understand"
    difficulty: str = "medium"
    position: int = 0
    bank_question_id: UUID | None = None   # provenance link to question_bank (Phase B)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


# Initial Elo rating per difficulty label — the bank self-calibrates from here.
DIFFICULTY_RATINGS = {"low": 1000.0, "medium": 1200.0, "high": 1400.0}
DEFAULT_RATING = 1200.0


@dataclass
class BankedQuestion:
    """A reusable, versioned assessment item persisted across quizzes.

    Reuse statistics make the bank self-calibrating: `p_value` is the
    empirical correct rate, and `difficulty_rating` is an Elo rating nudged
    after every response (Phase B)."""

    concept_name: str
    question_text: str
    id: UUID = field(default_factory=uuid4)
    concept_id: UUID | None = None
    question_type: str = "mcq"
    options: list[str] = field(default_factory=list)
    correct_answer: str = ""
    explanation: str = ""
    bloom_level: str = "Understand"
    difficulty: str = "medium"
    difficulty_rating: float = DEFAULT_RATING
    times_served: int = 0
    times_correct: int = 0
    version: int = 1
    source: str = "llm"
    is_active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def p_value(self) -> float | None:
        """Empirical difficulty: fraction answered correctly. None until served."""
        if self.times_served == 0:
            return None
        return round(self.times_correct / self.times_served, 3)

    def record_outcome(self, is_correct: bool) -> None:
        self.times_served += 1
        if is_correct:
            self.times_correct += 1
        self.updated_at = datetime.now(UTC)


@dataclass
class QuizAttempt:
    user_id: UUID
    quiz_id: UUID
    id: UUID = field(default_factory=uuid4)
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None
    score: float = 0.0
    correct_count: int = 0
    total_answered: int = 0
    total_time_ms: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def is_completed(self) -> bool:
        return self.completed_at is not None

    @property
    def accuracy(self) -> float:
        if self.total_answered == 0:
            return 0.0
        return round(self.correct_count / self.total_answered, 3)

    @property
    def passed(self) -> bool:
        return self.score >= 0.7


@dataclass
class QuizResponse:
    attempt_id: UUID
    question_id: UUID
    id: UUID = field(default_factory=uuid4)
    selected_answer: str = ""
    is_correct: bool = False
    time_spent_ms: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
