"""
Learner Intelligence — Evidence-driven questioning entities.

Pure domain objects for the QuestionEngine and the event-sourced evidence
layer. No I/O, no framework imports. Every mutation method that needs the
current time accepts an optional ``now`` argument so the logic is fully
deterministic and unit-testable.

Design contract (see the subsystem spec):
  - We infer *learner state* from accumulated *evidence*, never personality.
  - Evidence is append-only (event-sourced). State entities (RecallSchedule,
    LearnerPreference) are refined over repeated observations and must never
    be overwritten from a single interaction.
"""
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from math import exp
from uuid import UUID, uuid4

# ── Vocabularies ────────────────────────────────────────────────────────────────

# Why the QuestionEngine asks a question — it exists only to reduce uncertainty.
QUESTION_OBJECTIVES = [
    "verify_mastery",
    "verify_gap",
    "verify_memory",
    "verify_preference",
    "verify_confidence",
    "verify_retention",
    "advance_curriculum",
]

# The observed signal an interaction produced. Drives confidence + mastery.
EVIDENCE_SIGNALS = [
    "correct",
    "partial",
    "incorrect",
    "recall_success",
    "recall_fail",
    "misconception",
    "skipped",
    "preference_signal",
    "unknown",
]

# Where an evidence event originated.
EVIDENCE_SOURCES = ["chat", "question", "system"]

# Lifecycle of a generated question.
QUESTION_STATUSES = ["pending", "asked", "answered", "evaluated", "skipped", "expired"]

# Inferred learning-style preference dimensions (evidence-backed, not personality).
PREFERENCE_DIMENSIONS = [
    "visual",
    "worked_examples",
    "step_by_step",
    "interactive",
    "short",
    "detailed",
]

# How much a signal moves per-concept mastery/confidence, on a 0..1 scale.
_SIGNAL_WEIGHT = {
    "correct": 1.0,
    "recall_success": 1.0,
    "partial": 0.5,
    "preference_signal": 0.3,
    "incorrect": -1.0,
    "recall_fail": -1.0,
    "misconception": -1.0,
    "skipped": 0.0,
    "unknown": 0.0,
}


def signal_polarity(signal: str) -> float:
    """+1 / 0 / -1 direction of a signal on the learner-knows-it axis."""
    w = _SIGNAL_WEIGHT.get(signal, 0.0)
    return 1.0 if w > 0 else -1.0 if w < 0 else 0.0


# ── Evidence (append-only event) ────────────────────────────────────────────────

@dataclass
class LearnerEvidence:
    """A single observed fact about the learner. Immutable once written.

    Confidence is our certainty *about the learner's state* for this concept,
    not the learner's own confidence. ``confidence_before`` / ``confidence_after``
    snapshot how this event moved that certainty so the log is fully auditable.
    """
    user_id: UUID
    signal: str                              # one of EVIDENCE_SIGNALS
    id: UUID = field(default_factory=uuid4)
    concept_id: UUID | None = None
    concept_name: str | None = None
    objective: str = "verify_mastery"        # one of QUESTION_OBJECTIVES
    source: str = "question"                 # one of EVIDENCE_SOURCES
    weight: float = 1.0                      # evidence_weight, 0..1 reliability of this observation
    bloom_level: str = "Understand"
    intent: str = "unknown"
    question_id: UUID | None = None
    confidence_before: float = 0.0
    confidence_after: float = 0.0
    detail: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def confidence_delta(self) -> float:
        return round(self.confidence_after - self.confidence_before, 4)

    @property
    def polarity(self) -> float:
        return signal_polarity(self.signal)


# ── Answer evaluation (value object) ────────────────────────────────────────────

@dataclass
class AnswerEvaluation:
    """Result of grading a free-text answer against an expected answer.

    A value object — not persisted on its own; folded onto the GeneratedQuestion
    and turned into a LearnerEvidence event by the ConfidenceUpdater.
    """
    is_correct: bool
    score: float                     # 0..1 keyword/coverage overlap
    signal: str                      # correct | partial | incorrect
    feedback: str = ""
    matched: list[str] = field(default_factory=list)
    missed: list[str] = field(default_factory=list)

    @property
    def confidence_delta(self) -> float:
        """How strongly this answer should move assessment confidence, signed."""
        base = 0.35
        return round(base * self.score * signal_polarity(self.signal), 4)


# ── Generated question ──────────────────────────────────────────────────────────

@dataclass
class GeneratedQuestion:
    """An adaptive question generated solely to reduce uncertainty about one concept.

    Field set mirrors the QuestionOutput contract:
      question -> question_text, purpose -> objective (+ purpose text),
      concept -> concept_name, difficulty, bloom_level, expected_answer,
      confidence_threshold, evidence_weight.
    """
    user_id: UUID
    concept_id: UUID
    concept_name: str
    question_text: str
    id: UUID = field(default_factory=uuid4)
    objective: str = "verify_mastery"
    purpose: str = ""                        # human-readable reason we ask
    difficulty: str = "medium"               # low | medium | high
    bloom_level: str = "Understand"
    expected_answer: str = ""
    confidence_threshold: float = 0.6        # score needed to treat concept as verified
    evidence_weight: float = 1.0             # how much answering this counts toward state
    status: str = "pending"
    student_answer: str | None = None
    is_correct: bool | None = None
    score: float = 0.0
    feedback: str = ""
    scheduled_for: datetime | None = None
    asked_at: datetime | None = None
    answered_at: datetime | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def mark_asked(self, now: datetime | None = None) -> None:
        now = now or datetime.now(UTC)
        self.status = "asked"
        self.asked_at = now
        self.updated_at = now

    def mark_skipped(self, now: datetime | None = None) -> None:
        now = now or datetime.now(UTC)
        self.status = "skipped"
        self.updated_at = now

    def record_evaluation(
        self, answer: str, evaluation: AnswerEvaluation, now: datetime | None = None
    ) -> None:
        now = now or datetime.now(UTC)
        self.student_answer = answer
        self.is_correct = evaluation.is_correct
        self.score = round(evaluation.score, 3)
        self.feedback = evaluation.feedback
        self.status = "evaluated"
        self.answered_at = now
        self.updated_at = now

    @property
    def signal(self) -> str:
        """The evidence signal this evaluated question produced."""
        if self.status != "evaluated":
            return "unknown"
        if self.is_correct and self.score >= self.confidence_threshold:
            return "correct"
        if self.score > 0:
            return "partial"
        return "incorrect"

    @property
    def verifies_mastery(self) -> bool:
        return self.is_correct is True and self.score >= self.confidence_threshold


# ── Recall schedule (SM-2 spaced repetition) ────────────────────────────────────

_MIN_EASE = 1.3
_INITIAL_EASE = 2.5


@dataclass
class RecallSchedule:
    """Per-(learner, concept) spaced-repetition schedule.

    Implements the SM-2 algorithm to place ``next_review_at`` and estimates an
    Ebbinghaus retention probability so the QuestionEngine can trigger a
    ``verify_retention`` question exactly when memory is predicted to be decaying.
    """
    user_id: UUID
    concept_id: UUID
    concept_name: str
    id: UUID = field(default_factory=uuid4)
    interval_days: int = 0
    ease_factor: float = _INITIAL_EASE
    repetitions: int = 0
    lapses: int = 0
    retention_probability: float = 1.0
    last_reviewed: datetime | None = None
    next_review_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def review(self, quality: int, now: datetime | None = None) -> None:
        """Apply a review outcome. ``quality`` is 0..5 (>=3 is a pass, SM-2 convention)."""
        now = now or datetime.now(UTC)
        quality = max(0, min(5, quality))

        if quality < 3:
            self.repetitions = 0
            self.interval_days = 1
            self.lapses += 1
        else:
            if self.repetitions == 0:
                self.interval_days = 1
            elif self.repetitions == 1:
                self.interval_days = 6
            else:
                self.interval_days = max(1, round(self.interval_days * self.ease_factor))
            self.repetitions += 1

        # SM-2 ease update, clamped so a concept never becomes un-schedulable.
        self.ease_factor = max(
            _MIN_EASE,
            self.ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)),
        )
        self.ease_factor = round(self.ease_factor, 3)

        self.last_reviewed = now
        self.next_review_at = now + timedelta(days=self.interval_days)
        self.retention_probability = 1.0
        self.updated_at = now

    def retention_at(self, now: datetime | None = None) -> float:
        """Ebbinghaus forgetting curve: R = exp(-elapsed / stability).

        Stability grows with the current interval, so well-rehearsed concepts
        decay more slowly. Returns a 0..1 probability the learner still recalls it.
        """
        now = now or datetime.now(UTC)
        if self.last_reviewed is None:
            return 1.0
        elapsed_days = max(0.0, (now - self.last_reviewed).total_seconds() / 86400.0)
        stability = max(1.0, float(self.interval_days))
        return round(exp(-elapsed_days / stability), 4)

    def is_due(self, now: datetime | None = None) -> bool:
        now = now or datetime.now(UTC)
        return now >= self.next_review_at


# ── Inferred preference (evidence-backed) ───────────────────────────────────────

_MAX_SINGLE_STEP = 0.25   # a single observation can never move strength more than this
_CONFIDENCE_SATURATION = 5.0   # observations needed before we fully trust a preference


@dataclass
class LearnerPreference:
    """An inferred learning-style preference along one dimension.

    ``strength`` is 0..1 (how much the learner favours this style). ``confidence``
    is our certainty in that estimate and only grows with accumulated evidence.
    Refined via a damped update so no single interaction overwrites the state.
    """
    user_id: UUID
    dimension: str                           # one of PREFERENCE_DIMENSIONS
    id: UUID = field(default_factory=uuid4)
    strength: float = 0.5
    confidence: float = 0.0
    evidence_count: int = 0
    last_updated: datetime = field(default_factory=lambda: datetime.now(UTC))
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def observe(self, signal_strength: float, now: datetime | None = None) -> None:
        """Fold in one observation. ``signal_strength`` is 0..1 (target for this event)."""
        now = now or datetime.now(UTC)
        signal_strength = max(0.0, min(1.0, signal_strength))

        # Learning rate shrinks as evidence accumulates → refine, don't overwrite.
        alpha = min(_MAX_SINGLE_STEP, 1.0 / (self.evidence_count + 2))
        self.strength = round(self.strength + alpha * (signal_strength - self.strength), 4)
        self.evidence_count += 1
        self.confidence = round(min(1.0, self.evidence_count / _CONFIDENCE_SATURATION), 4)
        self.last_updated = now

    @property
    def is_reliable(self) -> bool:
        return self.evidence_count >= 3 and self.confidence >= 0.5
