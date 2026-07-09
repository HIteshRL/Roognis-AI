"""Unit tests for Phase A — psychometric capture."""
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.application.services.psychometric_assessment_service import (
    PsychometricAssessmentService,
)
from src.application.services.psychometric_questions import (
    QUESTIONS,
    TOTAL_QUESTIONS,
    is_valid_answer,
    likert_norm,
)
from src.domain.entities.learning import BehavioralSignals, StudentProfile
from src.domain.entities.psychometric import (
    SOURCE_INFERRED,
    SOURCE_SURVEY,
    PsychometricResponse,
)
from src.domain.exceptions import ValidationError

# ── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def repo():
    m = AsyncMock()
    m.answered_keys.return_value = set()
    m.list_responses.return_value = []
    return m


@pytest.fixture
def profile_repo():
    m = AsyncMock()
    m.get_by_user_id.return_value = None
    return m


@pytest.fixture
def svc(repo, profile_repo):
    return PsychometricAssessmentService(psychometric_repo=repo, profile_repo=profile_repo)


def _resp(key: str, dimension: str, value: str) -> PsychometricResponse:
    return PsychometricResponse(
        user_id=uuid4(), question_key=key, dimension=dimension, response_value=value
    )


# ── Question bank / helpers ─────────────────────────────────────────────────

def test_likert_norm_scale():
    assert likert_norm("1") == 0.0
    assert likert_norm("3") == 0.5
    assert likert_norm("5") == 1.0
    assert likert_norm("5", reverse=True) == 0.0
    assert likert_norm("1", reverse=True) == 1.0


def test_all_questions_have_unique_keys():
    keys = [q["key"] for q in QUESTIONS]
    assert len(keys) == len(set(keys))


def test_is_valid_answer_choice_and_likert():
    likert_q = next(q for q in QUESTIONS if q["type"] == "likert")
    assert is_valid_answer(likert_q, "3")
    assert not is_valid_answer(likert_q, "6")
    choice_q = next(q for q in QUESTIONS if q["type"] == "choice")
    valid = choice_q["options"][0]["value"]
    assert is_valid_answer(choice_q, valid)
    assert not is_valid_answer(choice_q, "nonsense")


# ── Incremental delivery ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_pending_questions_returns_first_n(svc, repo):
    repo.answered_keys.return_value = set()
    pending = await svc.get_pending_questions(uuid4(), limit=5)
    assert len(pending) == 5
    assert pending[0]["key"] == QUESTIONS[0]["key"]
    # scoring metadata is not leaked
    assert "reverse" not in pending[0]
    assert "orientation" not in pending[0]


@pytest.mark.asyncio
async def test_pending_excludes_answered(svc, repo):
    answered = {QUESTIONS[0]["key"], QUESTIONS[1]["key"]}
    repo.answered_keys.return_value = answered
    pending = await svc.get_pending_questions(uuid4(), limit=50)
    returned = {p["key"] for p in pending}
    assert answered.isdisjoint(returned)
    assert len(pending) == TOTAL_QUESTIONS - 2


# ── Rubric scoring (pure) ───────────────────────────────────────────────────

def test_motivation_intrinsic():
    by_key = {"mot_driver": "intrinsic", "mot_explore": "5", "mot_enjoy": "5", "mot_grades": "1"}
    surveyed, sources = PsychometricAssessmentService._score_surveyed(by_key)
    assert surveyed["motivation"]["type"] == "intrinsic"
    assert surveyed["motivation"]["strength"] >= 0.9
    assert sources["motivation"] == SOURCE_SURVEY


def test_motivation_extrinsic():
    by_key = {"mot_driver": "extrinsic", "mot_grades": "5", "mot_explore": "1", "mot_enjoy": "1"}
    surveyed, _ = PsychometricAssessmentService._score_surveyed(by_key)
    assert surveyed["motivation"]["type"] == "extrinsic"


def test_motivation_mixed_when_balanced():
    by_key = {"mot_driver": "mixed", "mot_explore": "3", "mot_grades": "3"}
    surveyed, _ = PsychometricAssessmentService._score_surveyed(by_key)
    assert surveyed["motivation"]["type"] == "mixed"


def test_discipline_high_with_reverse_item():
    # High on positive items, low on the reverse-scored distraction item
    by_key = {"dis_schedule": "5", "dis_finish": "5", "dis_breakdown": "5", "dis_distract": "1"}
    surveyed, _ = PsychometricAssessmentService._score_surveyed(by_key)
    assert surveyed["discipline"] >= 0.9


def test_discipline_low():
    by_key = {"dis_schedule": "1", "dis_finish": "1", "dis_breakdown": "1", "dis_distract": "5"}
    surveyed, _ = PsychometricAssessmentService._score_surveyed(by_key)
    assert surveyed["discipline"] <= 0.1


def test_confidence_reverse_handled():
    by_key = {"conf_master": "5", "conf_recover": "5", "conf_doubt": "1"}
    surveyed, _ = PsychometricAssessmentService._score_surveyed(by_key)
    assert surveyed["confidence"] >= 0.9


def test_interest_ranked_and_deduped():
    by_key = {"int_primary": "science_engineering", "int_secondary": "science_engineering"}
    surveyed, _ = PsychometricAssessmentService._score_surveyed(by_key)
    assert surveyed["interest"] == ["science_engineering"]

    by_key2 = {"int_primary": "mathematics", "int_secondary": "arts"}
    surveyed2, _ = PsychometricAssessmentService._score_surveyed(by_key2)
    assert surveyed2["interest"] == ["mathematics", "arts"]


def test_learning_style_primary_precedence():
    by_key = {"ls_primary": "visual", "ls_stuck": "reading"}
    surveyed, _ = PsychometricAssessmentService._score_surveyed(by_key)
    assert surveyed["learning_style"] == "visual"


# ── Merge: survey precedence over inferred ──────────────────────────────────

@pytest.mark.asyncio
async def test_get_profile_survey_beats_inferred(svc, repo, profile_repo):
    repo.list_responses.return_value = [
        _resp("dis_schedule", "discipline", "5"),
        _resp("dis_finish", "discipline", "5"),
        _resp("dis_breakdown", "discipline", "5"),
        _resp("dis_distract", "discipline", "1"),
    ]
    bs = BehavioralSignals(total_sessions=10, engagement_streak=1, sessions_per_day=0.2)
    profile_repo.get_by_user_id.return_value = StudentProfile(user_id=uuid4(), behavioral_signals=bs)

    prof = await svc.get_profile(uuid4())
    # Surveyed discipline is high; inferred would be low. Survey must win.
    assert prof.discipline >= 0.9
    assert prof.sources["discipline"] == SOURCE_SURVEY


@pytest.mark.asyncio
async def test_get_profile_inferred_fallback_when_empty(svc, repo, profile_repo):
    repo.list_responses.return_value = []
    bs = BehavioralSignals(
        total_sessions=8,
        engagement_streak=14,
        sessions_per_day=2.0,
        question_complexity_trend="rising",
        response_pattern="procedural",
        dominant_subject="Physics",
    )
    profile_repo.get_by_user_id.return_value = StudentProfile(user_id=uuid4(), behavioral_signals=bs)

    prof = await svc.get_profile(uuid4())
    assert prof.motivation_type == "intrinsic"
    assert prof.sources["motivation"] == SOURCE_INFERRED
    assert prof.discipline > 0.5
    assert prof.learning_style_preference == "hands_on"
    assert "Physics" in prof.interests
    assert prof.completeness == 0.0


@pytest.mark.asyncio
async def test_get_profile_no_behavior_no_survey_is_empty(svc, repo, profile_repo):
    repo.list_responses.return_value = []
    profile_repo.get_by_user_id.return_value = None
    prof = await svc.get_profile(uuid4())
    assert prof.is_empty
    assert prof.completeness == 0.0


@pytest.mark.asyncio
async def test_get_profile_sparse_behavior_not_inferred(svc, repo, profile_repo):
    repo.list_responses.return_value = []
    bs = BehavioralSignals(total_sessions=1, engagement_streak=1)
    profile_repo.get_by_user_id.return_value = StudentProfile(user_id=uuid4(), behavioral_signals=bs)
    prof = await svc.get_profile(uuid4())
    assert prof.is_empty  # < 3 sessions → no inference


# ── record_response ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_record_response_persists_and_scores(svc, repo, profile_repo):
    repo.list_responses.return_value = [_resp("ls_primary", "learning_style", "visual")]
    prof = await svc.record_response(uuid4(), "ls_primary", "visual")
    repo.upsert_response.assert_awaited_once()
    repo.save_profile.assert_awaited_once()
    assert prof.learning_style_preference == "visual"
    assert prof.completeness == round(1 / TOTAL_QUESTIONS, 3)


@pytest.mark.asyncio
async def test_record_response_rejects_unknown_key(svc):
    with pytest.raises(ValidationError):
        await svc.record_response(uuid4(), "does_not_exist", "1")


@pytest.mark.asyncio
async def test_record_response_rejects_bad_value(svc):
    with pytest.raises(ValidationError):
        await svc.record_response(uuid4(), "dis_schedule", "9")
