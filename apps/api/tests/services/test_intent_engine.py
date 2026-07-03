"""Unit tests for IntentEngine — rule-based intent classification."""
import pytest

from src.application.services.intent_engine import IntentEngine


@pytest.fixture
def engine():
    return IntentEngine()


def test_correction_request(engine):
    assert engine.classify("That's wrong, acceleration is not the same as velocity") == "correction_request"
    assert engine.classify("I think you made a mistake in step 2") == "correction_request"


def test_test_prep(engine):
    assert engine.classify("Give me practice questions for the maths exam") == "test_prep"
    assert engine.classify("What are important topics for revision?") == "test_prep"


def test_clarification(engine):
    assert engine.classify("I don't understand the explanation you gave") == "clarification"
    assert engine.classify("Can you explain that again in simpler terms?") == "clarification"


def test_problem_solving(engine):
    assert engine.classify("Solve the equation 2x + 5 = 11") == "problem_solving"
    assert engine.classify("Calculate the area of a circle with radius 5") == "problem_solving"
    assert engine.classify("How do I find the HCF of 36 and 48?") == "problem_solving"


def test_recall_short(engine):
    assert engine.classify("What is photosynthesis?") == "recall"
    assert engine.classify("Define osmosis") == "recall"


def test_concept_explanation_long_what_is(engine):
    # Long "what is" question should be concept_explanation not recall
    result = engine.classify("What is the relationship between force, mass and acceleration in Newton's second law?")
    assert result == "concept_explanation"


def test_concept_explanation(engine):
    assert engine.classify("Why does water expand when it freezes?") == "concept_explanation"
    assert engine.classify("Explain the difference between ionic and covalent bonds") == "concept_explanation"


def test_unknown_fallback(engine):
    result = engine.classify("hello")
    assert result == "unknown"


def test_empty_string(engine):
    result = engine.classify("")
    assert result == "unknown"


def test_classify_is_case_insensitive(engine):
    assert engine.classify("SOLVE the quadratic equation") == "problem_solving"
    assert engine.classify("What IS Newton's law?") == "recall"
