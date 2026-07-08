"""Static, versioned psychometric survey bank (roadmap v0.3).

Deterministic rubric — no LLM. Each item maps to exactly one dimension.
Two item types:

- ``likert``: answered 1–5 (Strongly disagree → Strongly agree). ``reverse``
  flips the scale. ``orientation`` (motivation items only) marks whether the
  item is evidence for the intrinsic or extrinsic pole.
- ``choice``: the client returns one option ``value``, which is itself the
  scored category (e.g. "visual", "intrinsic", "science_engineering").

Bumping ``QUESTION_BANK_VERSION`` after editing items lets the scorer and UI
detect stale response sets in future phases.
"""
from typing import Any

QUESTION_BANK_VERSION = 1

LIKERT_OPTIONS = [
    {"value": "1", "label": "Strongly disagree"},
    {"value": "2", "label": "Disagree"},
    {"value": "3", "label": "Neutral"},
    {"value": "4", "label": "Agree"},
    {"value": "5", "label": "Strongly agree"},
]

_INTEREST_OPTIONS = [
    {"value": "science_engineering", "label": "Science & engineering"},
    {"value": "mathematics", "label": "Mathematics & logic"},
    {"value": "technology", "label": "Technology & computing"},
    {"value": "humanities", "label": "History, languages & humanities"},
    {"value": "arts", "label": "Art, music & design"},
    {"value": "sports_health", "label": "Sports & health"},
]

_LEARNING_STYLE_OPTIONS = [
    {"value": "visual", "label": "Seeing diagrams, charts and visuals"},
    {"value": "verbal", "label": "Hearing an explanation out loud"},
    {"value": "hands_on", "label": "Trying it myself / practising"},
    {"value": "reading", "label": "Reading it written down"},
]

# Order matters: questions are served in this order for incremental onboarding.
QUESTIONS: list[dict[str, Any]] = [
    # ── Motivation ────────────────────────────────────────────────────────
    {
        "key": "mot_driver",
        "dimension": "motivation",
        "type": "choice",
        "text": "What makes you most want to study a topic?",
        "options": [
            {"value": "intrinsic", "label": "I find it genuinely interesting"},
            {"value": "extrinsic", "label": "I want good grades or exam results"},
            {"value": "mixed", "label": "Both matter about equally"},
        ],
    },
    {
        "key": "mot_explore",
        "dimension": "motivation",
        "type": "likert",
        "orientation": "intrinsic",
        "text": "I often explore topics beyond what is required.",
    },
    {
        "key": "mot_grades",
        "dimension": "motivation",
        "type": "likert",
        "orientation": "extrinsic",
        "text": "Grades and test scores strongly push me to study.",
    },
    {
        "key": "mot_enjoy",
        "dimension": "motivation",
        "type": "likert",
        "orientation": "intrinsic",
        "text": "I study mainly because I enjoy learning new things.",
    },
    # ── Discipline (self-regulation) ──────────────────────────────────────
    {
        "key": "dis_schedule",
        "dimension": "discipline",
        "type": "likert",
        "text": "I stick to a study routine even when I don't feel like it.",
    },
    {
        "key": "dis_finish",
        "dimension": "discipline",
        "type": "likert",
        "text": "I finish tasks I start, even the difficult ones.",
    },
    {
        "key": "dis_distract",
        "dimension": "discipline",
        "type": "likert",
        "reverse": True,
        "text": "I get distracted easily while studying.",
    },
    {
        "key": "dis_breakdown",
        "dimension": "discipline",
        "type": "likert",
        "text": "I break big tasks into small steps and work through them.",
    },
    # ── Interest ──────────────────────────────────────────────────────────
    {
        "key": "int_primary",
        "dimension": "interest",
        "type": "choice",
        "text": "Which area excites you the most?",
        "options": _INTEREST_OPTIONS,
    },
    {
        "key": "int_secondary",
        "dimension": "interest",
        "type": "choice",
        "text": "And which comes next?",
        "options": _INTEREST_OPTIONS,
    },
    # ── Learning style ────────────────────────────────────────────────────
    {
        "key": "ls_primary",
        "dimension": "learning_style",
        "type": "choice",
        "text": "How do you learn a new idea best?",
        "options": _LEARNING_STYLE_OPTIONS,
    },
    {
        "key": "ls_stuck",
        "dimension": "learning_style",
        "type": "choice",
        "text": "When you're stuck, what helps most?",
        "options": _LEARNING_STYLE_OPTIONS,
    },
    # ── Confidence ────────────────────────────────────────────────────────
    {
        "key": "conf_master",
        "dimension": "confidence",
        "type": "likert",
        "text": "With enough effort, I'm confident I can master difficult topics.",
    },
    {
        "key": "conf_doubt",
        "dimension": "confidence",
        "type": "likert",
        "reverse": True,
        "text": "I often doubt my ability to understand hard material.",
    },
    {
        "key": "conf_recover",
        "dimension": "confidence",
        "type": "likert",
        "text": "When I get something wrong, I believe I can figure out why.",
    },
]

QUESTIONS_BY_KEY: dict[str, dict[str, Any]] = {q["key"]: q for q in QUESTIONS}
TOTAL_QUESTIONS = len(QUESTIONS)

_LIKERT_VALUES = {"1", "2", "3", "4", "5"}


def public_question(q: dict[str, Any]) -> dict[str, Any]:
    """Client-facing shape — omits scoring metadata."""
    return {
        "key": q["key"],
        "dimension": q["dimension"],
        "type": q["type"],
        "text": q["text"],
        "options": q.get("options", LIKERT_OPTIONS if q["type"] == "likert" else []),
    }


def is_valid_answer(q: dict[str, Any], value: str) -> bool:
    if q["type"] == "likert":
        return value in _LIKERT_VALUES
    valid = {opt["value"] for opt in q.get("options", [])}
    return value in valid


def likert_norm(value: str, reverse: bool = False) -> float:
    """Map a 1–5 Likert answer to 0.0–1.0. Reverse flips the scale."""
    score = (int(value) - 1) / 4.0
    return round(1.0 - score if reverse else score, 4)
