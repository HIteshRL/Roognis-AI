"""Unit tests for LearnerContextService — Phase 0.3 profile-to-prompt injection."""
import pytest
from unittest.mock import AsyncMock
from uuid import uuid4

from src.application.services.learner_context_service import LearnerContextService
from src.domain.entities.learning import (
    BehavioralSignals,
    LearningGap,
    MasteryRecord,
    StudentProfile,
)


def make_profile(**kwargs) -> StudentProfile:
    defaults = dict(user_id=uuid4())
    defaults.update(kwargs)
    return StudentProfile(**defaults)


def make_mastery(**kwargs) -> MasteryRecord:
    defaults = dict(user_id=uuid4(), concept_id=uuid4(), concept_name="Fractions", score=20.0)
    defaults.update(kwargs)
    return MasteryRecord(**defaults)


def make_gap(**kwargs) -> LearningGap:
    defaults = dict(user_id=uuid4(), concept_id=uuid4(), concept_name="Fractions", severity="high")
    defaults.update(kwargs)
    return LearningGap(**defaults)


@pytest.fixture
def profile_repo():
    return AsyncMock()


@pytest.fixture
def mastery_repo():
    return AsyncMock()


@pytest.fixture
def gap_repo():
    return AsyncMock()


@pytest.fixture
def svc(profile_repo, mastery_repo, gap_repo):
    return LearnerContextService(profile_repo=profile_repo, mastery_repo=mastery_repo, gap_repo=gap_repo)


@pytest.mark.asyncio
async def test_returns_none_when_no_profile(svc, profile_repo):
    profile_repo.get_by_user_id.return_value = None
    result = await svc.build(uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_includes_identity_section(svc, profile_repo, mastery_repo, gap_repo):
    profile = make_profile(grade="9", current_chapter="Algebra", confidence_score=0.7)
    profile_repo.get_by_user_id.return_value = profile
    mastery_repo.list_by_user.return_value = []
    gap_repo.list_by_user.return_value = []

    result = await svc.build(uuid4())
    assert "### Identity" in result
    assert "Grade 9" in result
    assert "Algebra" in result
    assert "70%" in result


@pytest.mark.asyncio
async def test_includes_behavioral_patterns_when_enough_data(svc, profile_repo, mastery_repo, gap_repo):
    bs = BehavioralSignals(
        preferred_bloom_level="Apply",
        struggle_bloom_level="Analyze",
        response_pattern="procedural",
        total_sessions=10,
        sessions_per_day=2.0,
        engagement_streak=5,
        question_complexity_trend="rising",
    )
    profile = make_profile(grade="10", behavioral_signals=bs)
    profile_repo.get_by_user_id.return_value = profile
    mastery_repo.list_by_user.return_value = []
    gap_repo.list_by_user.return_value = []

    result = await svc.build(uuid4())
    assert "### Learning Patterns" in result
    assert "Apply" in result
    assert "Analyze" in result
    assert "procedural" in result
    assert "5-day streak" in result
    assert "rising" in result


@pytest.mark.asyncio
async def test_skips_patterns_section_with_few_sessions(svc, profile_repo, mastery_repo, gap_repo):
    bs = BehavioralSignals(total_sessions=2)
    profile = make_profile(grade="9", behavioral_signals=bs)
    profile_repo.get_by_user_id.return_value = profile
    mastery_repo.list_by_user.return_value = []
    gap_repo.list_by_user.return_value = []

    result = await svc.build(uuid4())
    assert "### Learning Patterns" not in result


@pytest.mark.asyncio
async def test_includes_weakest_concepts_with_scores(svc, profile_repo, mastery_repo, gap_repo):
    profile = make_profile(grade="9")
    profile_repo.get_by_user_id.return_value = profile
    mastery_repo.list_by_user.return_value = [
        make_mastery(concept_name="Strong", score=90.0),
        make_mastery(concept_name="Weak", score=35.0),
    ]
    gap_repo.list_by_user.return_value = []

    result = await svc.build(uuid4())
    assert "Weak (score 35)" in result
    assert "Strong" not in result or "Strengths" in result


@pytest.mark.asyncio
async def test_includes_misconceptions_with_details(svc, profile_repo, mastery_repo, gap_repo):
    profile = make_profile(grade="9")
    profile_repo.get_by_user_id.return_value = profile
    mastery_repo.list_by_user.return_value = []
    gap = make_gap(concept_name="Photosynthesis", severity="critical")
    gap.reason = "Students believe it happens at night"
    gap.occurrence_count = 4
    gap_repo.list_by_user.return_value = [gap]

    result = await svc.build(uuid4())
    assert "Photosynthesis" in result
    assert "critical severity" in result
    assert "4 occurrences" in result


@pytest.mark.asyncio
async def test_adaptation_instructions_procedural(svc, profile_repo, mastery_repo, gap_repo):
    bs = BehavioralSignals(response_pattern="procedural", total_sessions=5)
    profile = make_profile(grade="9", behavioral_signals=bs)
    profile_repo.get_by_user_id.return_value = profile
    mastery_repo.list_by_user.return_value = []
    gap_repo.list_by_user.return_value = []

    result = await svc.build(uuid4())
    assert "### How to Teach This Student" in result
    assert "worked examples" in result


@pytest.mark.asyncio
async def test_adaptation_instructions_conceptual(svc, profile_repo, mastery_repo, gap_repo):
    bs = BehavioralSignals(response_pattern="conceptual", total_sessions=5)
    profile = make_profile(grade="9", behavioral_signals=bs)
    profile_repo.get_by_user_id.return_value = profile
    mastery_repo.list_by_user.return_value = []
    gap_repo.list_by_user.return_value = []

    result = await svc.build(uuid4())
    assert "underlying principle" in result


@pytest.mark.asyncio
async def test_never_mentions_internal_context(svc, profile_repo, mastery_repo, gap_repo):
    bs = BehavioralSignals(total_sessions=5, response_pattern="mixed")
    profile = make_profile(grade="9", behavioral_signals=bs)
    profile_repo.get_by_user_id.return_value = profile
    mastery_repo.list_by_user.return_value = []
    gap_repo.list_by_user.return_value = []

    result = await svc.build(uuid4())
    assert "Do not mention this profile" in result


@pytest.mark.asyncio
async def test_gap_repo_called_with_unresolved_only(svc, profile_repo, mastery_repo, gap_repo):
    profile = make_profile(grade="9")
    profile_repo.get_by_user_id.return_value = profile
    mastery_repo.list_by_user.return_value = []
    gap_repo.list_by_user.return_value = []

    await svc.build(uuid4())
    gap_repo.list_by_user.assert_called_once()
    _, kwargs = gap_repo.list_by_user.call_args
    assert kwargs.get("include_resolved") is False
