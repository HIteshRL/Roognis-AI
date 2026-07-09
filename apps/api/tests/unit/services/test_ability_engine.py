"""Unit tests for the Elo AbilityEngine (Phase B)."""
from src.application.services.ability_engine import AbilityEngine


def test_expected_score_symmetry():
    assert AbilityEngine.expected_score(1200, 1200) == 0.5
    assert AbilityEngine.expected_score(1600, 1200) > 0.5   # stronger student
    assert AbilityEngine.expected_score(800, 1200) < 0.5    # weaker student


def test_always_correct_student_rises():
    engine = AbilityEngine()
    theta = 1200.0
    for _ in range(20):
        theta = engine.update(theta, 1200.0, is_correct=True).student_rating
    assert theta > 1200.0


def test_always_wrong_student_falls():
    engine = AbilityEngine()
    theta = 1200.0
    for _ in range(20):
        theta = engine.update(theta, 1200.0, is_correct=False).student_rating
    assert theta < 1200.0


def test_none_rating_starts_from_default():
    engine = AbilityEngine()
    up = engine.update(None, 1200.0, is_correct=True)
    assert up.expected == 0.5
    assert up.student_rating > 1200.0


def test_gain_shrinks_as_student_outclasses_question():
    engine = AbilityEngine()
    gain_even = engine.update(1200.0, 1200.0, is_correct=True).student_rating - 1200.0
    gain_strong = engine.update(1800.0, 1200.0, is_correct=True).student_rating - 1800.0
    assert 0 < gain_strong < gain_even


def test_question_rating_moves_opposite_to_student():
    engine = AbilityEngine()
    correct = engine.update(1200.0, 1200.0, is_correct=True)
    assert correct.question_rating < 1200.0   # answered right → looks easier
    wrong = engine.update(1200.0, 1200.0, is_correct=False)
    assert wrong.question_rating > 1200.0      # answered wrong → looks harder


def test_ratings_are_clamped():
    engine = AbilityEngine()
    theta = 2400.0
    for _ in range(50):
        theta = engine.update(theta, 1200.0, is_correct=True).student_rating
    assert theta <= 2400.0

    theta = 400.0
    for _ in range(50):
        theta = engine.update(theta, 1200.0, is_correct=False).student_rating
    assert theta >= 400.0
