from pydantic import BaseModel, Field

# ── Inbound ───────────────────────────────────────────────────────────────────

class SubmitResponseRequest(BaseModel):
    question_key: str
    value: str


# ── Outbound ──────────────────────────────────────────────────────────────────

class QuestionOption(BaseModel):
    value: str
    label: str


class PsychometricQuestion(BaseModel):
    key: str
    dimension: str
    type: str
    text: str
    options: list[QuestionOption] = Field(default_factory=list)


class PsychometricProfileResponse(BaseModel):
    motivation_type: str | None = None
    motivation_strength: float = 0.0
    discipline: float = 0.0
    interests: list[str] = Field(default_factory=list)
    learning_style_preference: str | None = None
    confidence_self_report: float = 0.0
    sources: dict[str, str] = Field(default_factory=dict)
    completeness: float = 0.0
    assessed_at: str | None = None
