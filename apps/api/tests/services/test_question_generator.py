"""Unit tests for QuestionGenerator — deterministic templated generation."""
from uuid import uuid4

from src.application.services.question_generator import QuestionGenerator


def test_generates_for_objective_and_sets_threshold():
    g = QuestionGenerator()
    q = g.generate(
        user_id=uuid4(), concept_id=uuid4(), concept_name="Fractions",
        objective="verify_retention", bloom_level="Understand", difficulty="medium",
    )
    assert q.objective == "verify_retention"
    assert q.confidence_threshold == 0.7
    assert "Fractions" in q.question_text
    assert q.question_text.lower().startswith("without looking it up")


def test_advance_curriculum_bumps_bloom():
    g = QuestionGenerator()
    q = g.generate(
        user_id=uuid4(), concept_id=uuid4(), concept_name="Vectors",
        objective="advance_curriculum", bloom_level="Understand",
    )
    # Understand (rank 1) is pushed up to Apply (rank 2).
    assert q.bloom_level == "Apply"
    assert q.confidence_threshold == 0.75


def test_difficulty_controls_evidence_weight():
    g = QuestionGenerator()
    low = g.generate(user_id=uuid4(), concept_id=uuid4(), concept_name="X", difficulty="low")
    high = g.generate(user_id=uuid4(), concept_id=uuid4(), concept_name="X", difficulty="high")
    assert high.evidence_weight > low.evidence_weight


def test_unknown_objective_falls_back_to_mastery():
    g = QuestionGenerator()
    q = g.generate(user_id=uuid4(), concept_id=uuid4(), concept_name="X", objective="nonsense")
    assert q.objective == "verify_mastery"


def test_expected_answer_defaults_to_concept():
    g = QuestionGenerator()
    q = g.generate(user_id=uuid4(), concept_id=uuid4(), concept_name="Osmosis")
    assert q.expected_answer == "Osmosis"
    q2 = g.generate(user_id=uuid4(), concept_id=uuid4(), concept_name="Osmosis",
                    expected_answer="water moves across a membrane")
    assert q2.expected_answer == "water moves across a membrane"
