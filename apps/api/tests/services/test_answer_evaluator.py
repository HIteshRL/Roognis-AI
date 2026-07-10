"""Unit tests for AnswerEvaluator — keyword-coverage grading (pure)."""
from uuid import uuid4

from src.application.services.answer_evaluator import AnswerEvaluator
from src.domain.entities.question import GeneratedQuestion


def make_question(expected: str, threshold: float = 0.6) -> GeneratedQuestion:
    return GeneratedQuestion(
        user_id=uuid4(), concept_id=uuid4(), concept_name="Photosynthesis",
        question_text="Explain photosynthesis.",
        expected_answer=expected, confidence_threshold=threshold,
    )


def test_correct_answer_matches_key_terms():
    e = AnswerEvaluator()
    q = make_question("photosynthesis converts sunlight into chemical energy")
    result = e.evaluate(q, "Photosynthesis converts sunlight into chemical energy in plants")
    assert result.is_correct is True
    assert result.signal == "correct"
    assert result.score >= 0.6


def test_partial_answer():
    e = AnswerEvaluator()
    q = make_question("photosynthesis converts sunlight chemical energy chlorophyll")
    result = e.evaluate(q, "photosynthesis uses sunlight")
    assert result.signal == "partial"
    assert 0.0 < result.score < 0.6
    assert result.missed


def test_incorrect_answer():
    e = AnswerEvaluator()
    q = make_question("mitochondria respiration adenosine")
    result = e.evaluate(q, "the sky is blue today")
    assert result.is_correct is False
    assert result.signal == "incorrect"
    assert result.score == 0.0


def test_empty_answer():
    e = AnswerEvaluator()
    q = make_question("anything relevant here")
    result = e.evaluate(q, "")
    assert result.signal == "incorrect"
    assert result.score == 0.0


def test_evaluation_is_case_insensitive():
    e = AnswerEvaluator()
    q = make_question("Newton second law force mass acceleration")
    result = e.evaluate(q, "FORCE equals MASS times ACCELERATION per newton second law")
    assert result.is_correct is True
