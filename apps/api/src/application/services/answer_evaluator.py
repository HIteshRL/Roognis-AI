"""
AnswerEvaluator — grades a free-text answer against a question's expected answer.

Pure and deterministic. Uses normalized keyword coverage: what fraction of the
salient terms in the expected answer appear in the learner's response. This keeps
evaluation zero-latency and fully unit-testable; a semantic/LLM grader can later
implement the same ``evaluate`` contract without touching callers.
"""
import re

from src.domain.entities.question import AnswerEvaluation, GeneratedQuestion

_STOPWORDS = {
    "the", "a", "an", "of", "to", "and", "or", "is", "are", "was", "were", "in",
    "on", "at", "it", "as", "by", "for", "with", "that", "this", "be", "how",
    "what", "why", "when", "which", "your", "you", "own", "words", "explain",
    "state", "show", "judge", "design", "break", "down", "using", "would",
}
_WORD_RE = re.compile(r"[a-z0-9]+")


def _terms(text: str) -> list[str]:
    return [w for w in _WORD_RE.findall(text.lower()) if w not in _STOPWORDS and len(w) > 2]


class AnswerEvaluator:
    def evaluate(self, question: GeneratedQuestion, answer: str) -> AnswerEvaluation:
        answer = (answer or "").strip()
        if not answer:
            return AnswerEvaluation(
                is_correct=False, score=0.0, signal="incorrect",
                feedback="No answer was provided.",
            )

        expected_terms = _terms(question.expected_answer or question.concept_name)
        if not expected_terms:
            # Nothing to match against — treat any substantive answer as partial evidence.
            substantive = len(_terms(answer)) >= 2
            return AnswerEvaluation(
                is_correct=substantive,
                score=0.5 if substantive else 0.0,
                signal="partial" if substantive else "incorrect",
                feedback="Answer recorded.",
            )

        answer_terms = set(_terms(answer))
        matched = [t for t in expected_terms if t in answer_terms]
        missed = [t for t in expected_terms if t not in answer_terms]
        score = round(len(matched) / len(expected_terms), 3)

        threshold = question.confidence_threshold
        if score >= threshold:
            signal, correct = "correct", True
            feedback = "Correct — that captures the key idea."
        elif score > 0:
            signal, correct = "partial", False
            feedback = "Partly there. You're missing: " + ", ".join(missed[:3]) + "."
        else:
            signal, correct = "incorrect", False
            feedback = "That doesn't match. Focus on: " + ", ".join(expected_terms[:3]) + "."

        return AnswerEvaluation(
            is_correct=correct,
            score=score,
            signal=signal,
            feedback=feedback,
            matched=matched,
            missed=missed,
        )
