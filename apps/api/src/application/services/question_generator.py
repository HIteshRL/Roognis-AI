"""
QuestionGenerator — builds a single adaptive question aimed at one objective.

Pure and deterministic (zero-latency, no LLM call in the hot path, mirroring the
IntentEngine decision). The generated ``expected_answer`` / ``key_terms`` fields
are hooks: a curriculum or LLM layer may pass richer values, but the engine
functions fully without them. A question exists only to reduce uncertainty about
one concept, so every field is chosen from the target objective + Bloom level.
"""
from uuid import UUID

from src.domain.entities.learning import BLOOM_LEVELS
from src.domain.entities.question import GeneratedQuestion

# Bloom-level verb that shapes the cognitive demand of the stem.
_BLOOM_STEM = {
    "Remember": "State",
    "Understand": "Explain in your own words",
    "Apply": "Show how you would use",
    "Analyze": "Break down",
    "Evaluate": "Judge whether",
    "Create": "Design an example using",
}

# Why we are asking — surfaced to the learner-facing purpose and the evidence log.
_OBJECTIVE_PURPOSE = {
    "verify_mastery": "Confirm the learner has mastered this concept.",
    "verify_gap": "Check whether a suspected misconception is real.",
    "verify_memory": "Verify which teaching approach the learner remembers.",
    "verify_preference": "Probe how the learner prefers to engage with this material.",
    "verify_confidence": "Reduce uncertainty about the learner's true grasp.",
    "verify_retention": "Test whether the learner still retains this after time.",
    "advance_curriculum": "Assess readiness to move to the next concept.",
}

# Higher-stakes objectives demand a higher score before we treat state as verified.
_OBJECTIVE_THRESHOLD = {
    "verify_mastery": 0.7,
    "verify_gap": 0.5,
    "verify_memory": 0.6,
    "verify_preference": 0.4,
    "verify_confidence": 0.6,
    "verify_retention": 0.7,
    "advance_curriculum": 0.75,
}

_DIFFICULTY_WEIGHT = {"low": 0.6, "medium": 0.8, "high": 1.0}


def _bloom_for(objective: str, mastery_score: float, fallback: str) -> str:
    """Retention/mastery checks probe at or below current level; advancement stretches up."""
    if fallback not in BLOOM_LEVELS:
        fallback = "Understand"
    rank = BLOOM_LEVELS.index(fallback)
    if objective == "advance_curriculum":
        rank = min(len(BLOOM_LEVELS) - 1, rank + 1)
    elif objective in ("verify_gap", "verify_confidence") and mastery_score < 40:
        rank = max(0, rank - 1)
    return BLOOM_LEVELS[rank]


class QuestionGenerator:
    def generate(
        self,
        user_id: UUID,
        concept_id: UUID,
        concept_name: str,
        objective: str = "verify_mastery",
        bloom_level: str = "Understand",
        difficulty: str = "medium",
        mastery_score: float = 0.0,
        expected_answer: str | None = None,
    ) -> GeneratedQuestion:
        if objective not in _OBJECTIVE_PURPOSE:
            objective = "verify_mastery"
        bloom = _bloom_for(objective, mastery_score, bloom_level)
        stem = _BLOOM_STEM.get(bloom, "Explain")

        if objective == "verify_retention":
            text = f"Without looking it up, {stem.lower()} what you remember about {concept_name}."
        elif objective == "verify_gap":
            text = f"{stem} {concept_name}. Walk through your reasoning so I can spot where it breaks."
        elif objective == "advance_curriculum":
            text = f"{stem} {concept_name} in a new situation you have not seen before."
        else:
            text = f"{stem} {concept_name}."

        return GeneratedQuestion(
            user_id=user_id,
            concept_id=concept_id,
            concept_name=concept_name,
            question_text=text,
            objective=objective,
            purpose=_OBJECTIVE_PURPOSE[objective],
            difficulty=difficulty if difficulty in _DIFFICULTY_WEIGHT else "medium",
            bloom_level=bloom,
            # expected_answer feeds the evaluator's keyword match; defaults to the concept.
            expected_answer=expected_answer or concept_name,
            confidence_threshold=_OBJECTIVE_THRESHOLD.get(objective, 0.6),
            evidence_weight=_DIFFICULTY_WEIGHT.get(difficulty, 0.8),
        )
