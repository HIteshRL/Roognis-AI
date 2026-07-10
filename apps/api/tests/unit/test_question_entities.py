"""Unit tests for the Learner Intelligence domain entities (pure logic)."""
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from src.domain.entities.question import (
    AnswerEvaluation,
    GeneratedQuestion,
    LearnerEvidence,
    LearnerPreference,
    RecallSchedule,
    signal_polarity,
)

T0 = datetime(2026, 1, 1, tzinfo=UTC)


def make_schedule(**kw) -> RecallSchedule:
    d = dict(user_id=uuid4(), concept_id=uuid4(), concept_name="Fractions")
    d.update(kw)
    return RecallSchedule(**d)


# ── RecallSchedule / SM-2 ────────────────────────────────────────────────────

def test_first_successful_review_sets_interval_one_day():
    s = make_schedule()
    s.review(quality=5, now=T0)
    assert s.repetitions == 1
    assert s.interval_days == 1
    assert s.next_review_at == T0 + timedelta(days=1)
    assert s.ease_factor == 2.6  # 2.5 + 0.1 at quality 5


def test_second_and_third_reviews_grow_interval():
    s = make_schedule()
    s.review(quality=5, now=T0)                       # interval 1
    s.review(quality=5, now=T0 + timedelta(days=1))   # interval 6
    assert s.interval_days == 6
    # SM-2 computes the new interval from the CURRENT ease, then bumps ease.
    ease_before = s.ease_factor
    s.review(quality=5, now=T0 + timedelta(days=7))
    assert s.interval_days == round(6 * ease_before)
    assert s.repetitions == 3


def test_failed_review_resets_and_records_lapse():
    s = make_schedule()
    s.review(quality=5, now=T0)
    s.review(quality=5, now=T0 + timedelta(days=1))
    s.review(quality=2, now=T0 + timedelta(days=7))   # failure
    assert s.repetitions == 0
    assert s.interval_days == 1
    assert s.lapses == 1


def test_ease_factor_never_below_floor():
    s = make_schedule()
    for i in range(10):
        s.review(quality=0, now=T0 + timedelta(days=i))
    assert s.ease_factor >= 1.3


def test_retention_decays_over_time():
    s = make_schedule()
    s.review(quality=5, now=T0)  # interval 1 day
    assert s.retention_at(T0) == 1.0
    later = s.retention_at(T0 + timedelta(days=1))
    assert 0.0 < later < 1.0


def test_is_due():
    s = make_schedule()
    s.review(quality=5, now=T0)
    assert s.is_due(T0 + timedelta(days=2)) is True
    assert s.is_due(T0 + timedelta(hours=1)) is False


# ── LearnerPreference ────────────────────────────────────────────────────────

def test_single_observation_cannot_overwrite_state():
    p = LearnerPreference(user_id=uuid4(), dimension="step_by_step")
    p.observe(1.0, now=T0)
    # Damped: starts at 0.5, moves by at most 0.25 on the first observation.
    assert p.strength == 0.625
    assert p.evidence_count == 1
    assert p.confidence == 0.2


def test_confidence_grows_and_becomes_reliable():
    p = LearnerPreference(user_id=uuid4(), dimension="visual")
    for _ in range(3):
        p.observe(1.0, now=T0)
    assert p.evidence_count == 3
    assert p.confidence >= 0.5
    assert p.is_reliable is True


def test_repeated_observations_converge_toward_signal():
    p = LearnerPreference(user_id=uuid4(), dimension="short")
    for _ in range(20):
        p.observe(1.0, now=T0)
    assert p.strength > 0.9  # refines toward the repeated signal


# ── GeneratedQuestion + AnswerEvaluation ─────────────────────────────────────

def make_question(**kw) -> GeneratedQuestion:
    d = dict(user_id=uuid4(), concept_id=uuid4(), concept_name="Photosynthesis",
             question_text="Explain photosynthesis.", confidence_threshold=0.6)
    d.update(kw)
    return GeneratedQuestion(**d)


def test_question_signal_correct():
    q = make_question()
    q.record_evaluation("ans", AnswerEvaluation(is_correct=True, score=0.9, signal="correct"), now=T0)
    assert q.status == "evaluated"
    assert q.signal == "correct"
    assert q.verifies_mastery is True


def test_question_signal_partial():
    q = make_question()
    q.record_evaluation("ans", AnswerEvaluation(is_correct=False, score=0.4, signal="partial"), now=T0)
    assert q.signal == "partial"
    assert q.verifies_mastery is False


def test_question_signal_incorrect():
    q = make_question()
    q.record_evaluation("", AnswerEvaluation(is_correct=False, score=0.0, signal="incorrect"), now=T0)
    assert q.signal == "incorrect"


def test_unevaluated_question_signal_is_unknown():
    q = make_question()
    assert q.signal == "unknown"


def test_answer_evaluation_confidence_delta_signed():
    correct = AnswerEvaluation(is_correct=True, score=1.0, signal="correct")
    wrong = AnswerEvaluation(is_correct=False, score=0.0, signal="incorrect")
    assert correct.confidence_delta > 0
    assert wrong.confidence_delta <= 0


# ── Evidence ─────────────────────────────────────────────────────────────────

def test_evidence_confidence_delta_and_polarity():
    e = LearnerEvidence(
        user_id=uuid4(), signal="correct",
        confidence_before=0.2, confidence_after=0.55,
    )
    assert e.confidence_delta == 0.35
    assert e.polarity == 1.0


def test_signal_polarity_map():
    assert signal_polarity("correct") == 1.0
    assert signal_polarity("misconception") == -1.0
    assert signal_polarity("unknown") == 0.0
