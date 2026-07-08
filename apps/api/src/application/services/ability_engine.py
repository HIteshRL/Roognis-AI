"""Phase B — Elo-style ability tracking (IRT-lite).

Full IRT needs calibration data the platform doesn't have yet. Elo is the
well-proven adaptive-learning stand-in: it converges from a single response,
self-calibrates the question bank as a side effect, and is upgradeable to IRT
later *without a schema change* (θ and difficulty_rating map onto IRT ability
and difficulty).

Pure math — no I/O. Callers persist the returned values.
"""
from dataclasses import dataclass

from src.domain.entities.quiz import DEFAULT_RATING

# K-factors: the student's θ moves faster than a bank question's rating, since
# one question accumulates far more responses than one student answers of it.
_K_STUDENT = 32.0
_K_QUESTION = 16.0
_LOGISTIC_SCALE = 400.0

# Keep ratings in a sane band so a streak can't run θ to infinity.
_MIN_RATING = 400.0
_MAX_RATING = 2400.0


@dataclass
class AbilityUpdate:
    student_rating: float
    question_rating: float
    expected: float          # P(correct) the model assigned before the outcome


class AbilityEngine:
    """Symmetric Elo update between a student's per-concept ability θ and a
    question's difficulty rating."""

    def __init__(
        self,
        k_student: float = _K_STUDENT,
        k_question: float = _K_QUESTION,
    ) -> None:
        self._k_student = k_student
        self._k_question = k_question

    @staticmethod
    def expected_score(student_rating: float, question_rating: float) -> float:
        """Logistic probability the student answers correctly."""
        return 1.0 / (1.0 + 10 ** ((question_rating - student_rating) / _LOGISTIC_SCALE))

    def update(
        self,
        student_rating: float | None,
        question_rating: float,
        is_correct: bool,
    ) -> AbilityUpdate:
        theta = student_rating if student_rating is not None else DEFAULT_RATING
        expected = self.expected_score(theta, question_rating)
        outcome = 1.0 if is_correct else 0.0

        new_theta = _clamp(theta + self._k_student * (outcome - expected))
        # Question moves opposite to the student: a correct answer makes it
        # look easier, a wrong one harder.
        new_q = _clamp(question_rating - self._k_question * (outcome - expected))

        return AbilityUpdate(
            student_rating=round(new_theta, 1),
            question_rating=round(new_q, 1),
            expected=round(expected, 4),
        )


def _clamp(rating: float) -> float:
    return max(_MIN_RATING, min(_MAX_RATING, rating))
