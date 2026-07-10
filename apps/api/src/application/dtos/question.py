"""Pydantic request/response contracts for the Learner Intelligence subsystem."""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

# ── Inbound ───────────────────────────────────────────────────────────────────

class SubmitAnswerRequest(BaseModel):
    answer: str = Field(min_length=1, max_length=5000)


class BridgeEvidenceRequest(BaseModel):
    """Evidence forwarded from an external surface (e.g. the standalone demo).

    ``external_ref`` identifies the learner in the source system; it is mapped to
    a namespaced bridge user so the real engine tracks per-learner state.
    """
    external_ref: str = Field(min_length=1, max_length=120)
    concept_name: str = Field(min_length=1, max_length=200)
    signal: str = Field(min_length=1, max_length=30)
    objective: str = "verify_confidence"
    source: str = "question"
    weight: float = 1.0
    bloom_level: str = "Understand"
    intent: str = "unknown"
    detail: str = Field(default="", max_length=2000)


# ── Outbound ──────────────────────────────────────────────────────────────────

class GeneratedQuestionResponse(BaseModel):
    """Mirrors the QuestionOutput contract."""
    id: UUID
    concept_id: UUID
    concept: str                     # concept_name
    question: str                    # question_text
    purpose: str
    objective: str
    difficulty: str
    bloom_level: str
    confidence_threshold: float
    evidence_weight: float
    status: str
    created_at: datetime


class AnswerEvaluationResponse(BaseModel):
    is_correct: bool
    score: float
    signal: str
    feedback: str
    matched: list[str] = Field(default_factory=list)
    missed: list[str] = Field(default_factory=list)


class SubmissionResponse(BaseModel):
    question_id: UUID
    concept: str
    evaluation: AnswerEvaluationResponse
    confidence_after: float


class QuestionHistoryItem(BaseModel):
    id: UUID
    concept: str
    question: str
    objective: str
    status: str
    is_correct: bool | None
    score: float
    created_at: datetime


class RecallScheduleResponse(BaseModel):
    concept_id: UUID
    concept_name: str
    interval_days: int
    ease_factor: float
    repetitions: int
    lapses: int
    retention_probability: float
    next_review_at: datetime
    is_due: bool


class LearnerPreferenceResponse(BaseModel):
    dimension: str
    strength: float
    confidence: float
    evidence_count: int
    is_reliable: bool
    last_updated: datetime


class EvidenceResponse(BaseModel):
    id: UUID
    concept_name: str | None
    signal: str
    objective: str
    source: str
    weight: float
    confidence_before: float
    confidence_after: float
    confidence_delta: float
    detail: str
    created_at: datetime


class LearnerContextResponse(BaseModel):
    user_id: UUID
    weak_concepts: list[dict] = Field(default_factory=list)
    persistent_gaps: list[dict] = Field(default_factory=list)
    preferences: list[dict] = Field(default_factory=list)
    current_goal: dict | None = None
    memory_state: dict = Field(default_factory=dict)
    recommendations: list[dict] = Field(default_factory=list)
