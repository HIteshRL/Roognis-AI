"""Phase A — Psychometric capture (roadmap v0.3).

Measured (not merely inferred) psychographic dimensions for a student:
motivation orientation, self-regulation (discipline), topic interests,
learning-style preference, and self-reported confidence.

`PsychometricProfile` is stored as JSONB on `student_profiles`; each
individual survey answer is persisted as a `PsychometricResponse` row so the
rubric can be recomputed and audited. Both are pure dataclasses — no I/O.
"""
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

# Dimension keys — used as the source-map keys and in the prompt block.
DIMENSIONS = ("motivation", "discipline", "interest", "learning_style", "confidence")

# How a dimension's value was determined.
SOURCE_SURVEY = "survey"
SOURCE_INFERRED = "inferred"
SOURCE_BLENDED = "blended"


@dataclass
class PsychometricProfile:
    """Merged psychographic view. Any dimension may be surveyed or inferred;
    `sources` records provenance per dimension so the UI and prompt can be
    honest about confidence."""

    motivation_type: str | None = None        # intrinsic | extrinsic | mixed
    motivation_strength: float = 0.0          # 0–1, magnitude of the dominant drive
    discipline: float = 0.0                   # 0–1 self-regulation
    interests: list[str] = field(default_factory=list)   # ranked topic affinities
    learning_style_preference: str | None = None         # visual | verbal | hands_on | reading
    confidence_self_report: float = 0.0       # 0–1
    sources: dict[str, str] = field(default_factory=dict)  # dimension -> survey|inferred|blended
    completeness: float = 0.0                 # fraction of the survey answered (0–1)
    assessed_at: str | None = None

    @property
    def is_empty(self) -> bool:
        return not self.sources

    def to_dict(self) -> dict[str, Any]:
        return {
            "motivation_type": self.motivation_type,
            "motivation_strength": self.motivation_strength,
            "discipline": self.discipline,
            "interests": self.interests,
            "learning_style_preference": self.learning_style_preference,
            "confidence_self_report": self.confidence_self_report,
            "sources": self.sources,
            "completeness": self.completeness,
            "assessed_at": self.assessed_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "PsychometricProfile":
        if not data:
            return cls()
        return cls(
            motivation_type=data.get("motivation_type"),
            motivation_strength=data.get("motivation_strength", 0.0),
            discipline=data.get("discipline", 0.0),
            interests=data.get("interests", []),
            learning_style_preference=data.get("learning_style_preference"),
            confidence_self_report=data.get("confidence_self_report", 0.0),
            sources=data.get("sources", {}),
            completeness=data.get("completeness", 0.0),
            assessed_at=data.get("assessed_at"),
        )


@dataclass
class PsychometricResponse:
    """A single survey answer, stored per-question (roadmap v0.3: response storage)."""

    user_id: UUID
    question_key: str
    dimension: str
    response_value: str          # normalized value (likert "1"–"5" or a choice category)
    id: UUID = field(default_factory=uuid4)
    question_text: str | None = None
    response_raw: str | None = None   # original client payload, for audit
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
