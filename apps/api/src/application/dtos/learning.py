from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

# ── Inbound ───────────────────────────────────────────────────────────────────

class UpdateProfileRequest(BaseModel):
    institution: str | None = None
    grade: str | None = None
    subjects: list[str] = Field(default_factory=list)
    current_chapter: str | None = None


# ── Outbound ──────────────────────────────────────────────────────────────────

class BehavioralSignalsResponse(BaseModel):
    preferred_bloom_level: str | None = None
    struggle_bloom_level: str | None = None
    avg_session_duration_ms: int = 0
    sessions_per_day: float = 0.0
    question_complexity_trend: str = "stable"
    dominant_subject: str | None = None
    total_sessions: int = 0
    total_misconceptions: int = 0
    engagement_streak: int = 0
    strengths: list[str] = Field(default_factory=list)
    recent_topics: list[str] = Field(default_factory=list)
    response_pattern: str = "unknown"


class StudentProfileResponse(BaseModel):
    id: UUID
    user_id: UUID
    institution: str | None
    grade: str | None
    subjects: list[str]
    current_chapter: str | None
    learning_velocity: float
    confidence_score: float
    behavioral_signals: BehavioralSignalsResponse = Field(default_factory=BehavioralSignalsResponse)
    last_active: datetime
    created_at: datetime
    updated_at: datetime


class LearningSessionResponse(BaseModel):
    id: UUID
    user_id: UUID
    conversation_id: UUID | None
    subject: str | None
    chapter: str | None
    grade: str | None
    question: str
    primary_concept: str | None
    concepts_discussed: list[str]
    bloom_level: str
    difficulty_level: str
    misconceptions: list[str]
    intent: str = "unknown"
    token_count: int
    duration_ms: int
    created_at: datetime


class MasteryRecordResponse(BaseModel):
    id: UUID
    concept_id: UUID
    concept_name: str
    score: float
    label: str           # mastered | developing | emerging | not_started
    interaction_count: int
    last_updated: datetime


class LearningGapResponse(BaseModel):
    id: UUID
    concept_id: UUID
    concept_name: str
    severity: str        # low | medium | high | critical
    reason: str
    confidence: str
    occurrence_count: int
    is_resolved: bool
    created_at: datetime
    updated_at: datetime


class ConceptNodeResponse(BaseModel):
    id: UUID
    name: str
    subject: str | None
    grade: str | None
    chapter: str | None
    bloom_level: str
    difficulty: str


class RecommendationResponse(BaseModel):
    concept_id: UUID
    concept_name: str
    subject: str | None
    chapter: str | None
    reason: str
    readiness_score: float     # 0–1, how ready the student is


class RetentionRiskResponse(BaseModel):
    concept_id: UUID
    concept_name: str
    score: float
    days_since_reinforced: int
    risk: float          # 0-1, higher = more likely to have decayed


class LearningAnalyticsResponse(BaseModel):
    user_id: UUID
    total_sessions: int
    total_concepts_encountered: int
    average_mastery: float
    mastered_count: int
    developing_count: int
    emerging_count: int
    not_started_count: int
    active_gaps: int
    critical_gaps: int
    recent_bloom_levels: dict[str, int]   # bloom_level -> count last 7 days
    recent_concepts: list[str]
    velocity_trend: float = 0.0                              # points/day over last 7 days
    at_risk_concepts: list[RetentionRiskResponse] = Field(default_factory=list)


class SessionListResponse(BaseModel):
    sessions: list[LearningSessionResponse]
    total: int
    limit: int
    offset: int


class ConceptExtractionResult(BaseModel):
    primary_concept: str
    secondary_concepts: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    bloom_level: str = "Understand"
    difficulty: str = "medium"
    misconceptions: list[str] = Field(default_factory=list)


class ConceptMemoryResponse(BaseModel):
    id: UUID
    concept_id: UUID
    concept_name: str
    times_taught: int
    successful_approaches: int
    failed_approaches: int
    last_approach: str | None
    teaching_notes: list[str]
    success_rate: float
    needs_different_approach: bool
    last_taught: datetime


class LearningPathNodeResponse(BaseModel):
    concept_id: UUID
    concept_name: str
    subject: str | None
    chapter: str | None
    bloom_level: str
    difficulty: str


class LearningPathResponse(BaseModel):
    target_concept_id: UUID | None = None
    path: list[LearningPathNodeResponse]
    frontier: list[RecommendationResponse]
    coverage: dict[str, dict] = Field(default_factory=dict)


class SkillEntry(BaseModel):
    skill: str
    proficiency: float


class SkillProfileResponse(BaseModel):
    skill_profile: dict[str, float]
    top_skills: list[SkillEntry]
    bloom_distribution: dict[str, int]
