"""Result types for the guarded, agentic RAG flow."""
from dataclasses import dataclass, field
from typing import Literal

Decision = Literal["answered", "blocked_unsafe", "off_topic", "not_in_chapter", "error"]


@dataclass
class SafetyVerdict:
    blocked: bool
    category: str | None = None
    message: str | None = None


@dataclass
class RelevanceVerdict:
    on_topic: bool
    confidence: float
    reason: str


@dataclass
class GroundingVerdict:
    concept_present: bool
    confidence: float
    decision: Literal["ANSWER", "NOT_IN_CHAPTER"]
    reason: str
    missing: str | None = None


@dataclass
class GuardedAnswer:
    decision: Decision
    answer: str | None = None
    message: str | None = None            # child-facing text for non-answer decisions
    sources: list[dict] = field(default_factory=list)
    trail: dict = field(default_factory=dict)  # observability: which gate decided and why
