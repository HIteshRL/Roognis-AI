"""
Self-contained inline QuestionEngine for the standalone demo.

Deliberately dependency-free (stdlib only) because the demo cannot import
apps/api's ``src`` package — it collides with rag-standalone's ``src`` on
sys.path. The generation + evaluation logic mirrors
apps/api/src/application/services/question_generator.py and answer_evaluator.py
exactly, and the output dict matches the QuestionOutput contract field-for-field
so evidence can be bridged to the real engine 1:1 (see bridge.py).
"""
import re

BLOOM_LEVELS = ["Remember", "Understand", "Apply", "Analyze", "Evaluate", "Create"]

_BLOOM_STEM = {
    "Remember": "State",
    "Understand": "Explain in your own words",
    "Apply": "Show how you would use",
    "Analyze": "Break down",
    "Evaluate": "Judge whether",
    "Create": "Design an example using",
}

_OBJECTIVE_PURPOSE = {
    "verify_mastery": "Confirm you've mastered this concept.",
    "verify_gap": "Check whether a suspected misconception is real.",
    "verify_confidence": "Reduce uncertainty about your grasp of this.",
    "verify_retention": "Test whether you still remember this.",
    "advance_curriculum": "Check readiness to move on.",
}

_OBJECTIVE_THRESHOLD = {
    "verify_mastery": 0.7,
    "verify_gap": 0.5,
    "verify_confidence": 0.6,
    "verify_retention": 0.7,
    "advance_curriculum": 0.75,
}

_DIFFICULTY_WEIGHT = {"low": 0.6, "medium": 0.8, "high": 1.0}

_STOPWORDS = {
    "the", "a", "an", "of", "to", "and", "or", "is", "are", "was", "were", "in",
    "on", "at", "it", "as", "by", "for", "with", "that", "this", "be", "how",
    "what", "why", "when", "which", "your", "you", "own", "words", "explain",
    "state", "show", "judge", "design", "break", "down", "using", "would",
}
_WORD_RE = re.compile(r"[a-z0-9]+")


def _terms(text: str) -> list[str]:
    return [w for w in _WORD_RE.findall((text or "").lower())
            if w not in _STOPWORDS and len(w) > 2]


def _bloom_for(objective: str, mastery_score: float, fallback: str) -> str:
    if fallback not in BLOOM_LEVELS:
        fallback = "Understand"
    rank = BLOOM_LEVELS.index(fallback)
    if objective == "advance_curriculum":
        rank = min(len(BLOOM_LEVELS) - 1, rank + 1)
    elif objective in ("verify_gap", "verify_confidence") and mastery_score < 40:
        rank = max(0, rank - 1)
    return BLOOM_LEVELS[rank]


def generate(
    concept: str,
    objective: str = "verify_confidence",
    bloom_level: str = "Understand",
    difficulty: str = "medium",
    mastery_score: float = 0.0,
    expected_answer: str | None = None,
) -> dict:
    """Return a QuestionOutput dict for one concept + objective."""
    if objective not in _OBJECTIVE_PURPOSE:
        objective = "verify_confidence"
    bloom = _bloom_for(objective, mastery_score, bloom_level)
    stem = _BLOOM_STEM.get(bloom, "Explain")

    if objective == "verify_retention":
        text = f"Without looking it up, {stem.lower()} what you remember about {concept}."
    elif objective == "verify_gap":
        text = f"{stem} {concept}. Walk through your reasoning so I can spot where it breaks."
    elif objective == "advance_curriculum":
        text = f"{stem} {concept} in a new situation you haven't seen before."
    else:
        text = f"{stem} {concept}."

    return {
        "concept": concept,
        "question": text,
        "objective": objective,
        "purpose": _OBJECTIVE_PURPOSE[objective],
        "difficulty": difficulty if difficulty in _DIFFICULTY_WEIGHT else "medium",
        "bloom_level": bloom,
        "expected_answer": expected_answer or concept,
        "confidence_threshold": _OBJECTIVE_THRESHOLD.get(objective, 0.6),
        "evidence_weight": _DIFFICULTY_WEIGHT.get(difficulty, 0.8),
    }


def evaluate(expected_answer: str, concept: str, confidence_threshold: float, answer: str) -> dict:
    """Grade a free-text answer by keyword coverage. Mirrors apps/api AnswerEvaluator."""
    answer = (answer or "").strip()
    if not answer:
        return {"is_correct": False, "score": 0.0, "signal": "incorrect",
                "feedback": "No answer was provided.", "matched": [], "missed": []}

    expected_terms = _terms(expected_answer or concept)
    if not expected_terms:
        substantive = len(_terms(answer)) >= 2
        return {"is_correct": substantive, "score": 0.5 if substantive else 0.0,
                "signal": "partial" if substantive else "incorrect",
                "feedback": "Answer recorded.", "matched": [], "missed": []}

    answer_terms = set(_terms(answer))
    matched = [t for t in expected_terms if t in answer_terms]
    missed = [t for t in expected_terms if t not in answer_terms]
    score = round(len(matched) / len(expected_terms), 3)

    if score >= confidence_threshold:
        signal, correct = "correct", True
        feedback = "Correct — that captures the key idea."
    elif score > 0:
        signal, correct = "partial", False
        feedback = "Partly there. You're missing: " + ", ".join(missed[:3]) + "."
    else:
        signal, correct = "incorrect", False
        feedback = "Not quite. Focus on: " + ", ".join(expected_terms[:3]) + "."

    return {"is_correct": correct, "score": score, "signal": signal,
            "feedback": feedback, "matched": matched, "missed": missed}


_POLARITY = {"correct": 1.0, "recall_success": 1.0, "partial": 0.5,
             "incorrect": -1.0, "misconception": -1.0, "recall_fail": -1.0}


def concept_confidence(events: list[dict]) -> float:
    """Assessment confidence = agreement × coverage over evidence. Mirrors apps/api."""
    directional = [(e, _POLARITY.get(e.get("signal", ""), 0.0)) for e in events]
    directional = [(e, p) for e, p in directional if p != 0.0]
    if not directional:
        return 0.0
    pos = sum(e.get("weight", 1.0) for e, p in directional if p > 0)
    neg = sum(e.get("weight", 1.0) for e, p in directional if p < 0)
    total = pos + neg
    if total <= 0:
        return 0.0
    agreement = abs(pos - neg) / total
    coverage = min(1.0, len(directional) / 4.0)
    return round(agreement * coverage, 4)
