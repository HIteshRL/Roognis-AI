from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

# ── Inbound ──────────────────────────────────────────────────────────────────


class GenerateQuizRequest(BaseModel):
    subject: str | None = None
    chapter: str | None = None
    concept_ids: list[str] | None = None
    question_count: int = Field(default=5, ge=1, le=10)
    difficulty: str = "adaptive"


class SubmitResponseItem(BaseModel):
    question_id: str
    selected_answer: str
    time_spent_ms: int = 0


class SubmitQuizRequest(BaseModel):
    responses: list[SubmitResponseItem]


# ── Outbound ─────────────────────────────────────────────────────────────────


class QuizSummaryResponse(BaseModel):
    id: UUID
    title: str
    subject: str | None
    chapter: str | None
    difficulty: str
    question_count: int
    total_attempts: int
    best_score: float
    created_at: datetime


class QuizQuestionResponse(BaseModel):
    id: UUID
    concept_name: str
    question_text: str
    question_type: str
    options: list[str]
    bloom_level: str
    difficulty: str
    position: int


class QuizDetailResponse(BaseModel):
    id: UUID
    title: str
    subject: str | None
    chapter: str | None
    difficulty: str
    question_count: int
    questions: list[QuizQuestionResponse]
    created_at: datetime


class QuizAttemptResponse(BaseModel):
    id: UUID
    quiz_id: UUID
    score: float
    correct_count: int
    total_answered: int
    total_time_ms: int
    started_at: datetime
    completed_at: datetime | None


class QuestionResultResponse(BaseModel):
    question_id: UUID
    question_text: str
    options: list[str]
    selected_answer: str
    correct_answer: str
    is_correct: bool
    explanation: str
    concept_name: str


class QuizResultResponse(BaseModel):
    attempt: QuizAttemptResponse
    quiz_title: str
    quiz_subject: str | None
    results: list[QuestionResultResponse]
