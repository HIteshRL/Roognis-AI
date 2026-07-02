"""Unit tests for LearningVelocityService — Phase 0.4 velocity trend + retention risk."""
import pytest
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

from src.application.services.learning_velocity_service import LearningVelocityService
from src.domain.entities.learning import LearningSession, MasteryRecord


def make_session(**kwargs) -> LearningSession:
    defaults = dict(
        user_id=uuid4(),
        question="q",
        ai_response="a",
        bloom_level="Understand",
        misconceptions=[],
    )
    defaults.update(kwargs)
    return LearningSession(**defaults)


def make_mastery(**kwargs) -> MasteryRecord:
    defaults = dict(
        user_id=uuid4(),
        concept_id=uuid4(),
        concept_name="Concept",
        score=80.0,
        last_updated=datetime.now(UTC),
    )
    defaults.update(kwargs)
    return MasteryRecord(**defaults)


@pytest.fixture
def session_repo():
    return AsyncMock()


@pytest.fixture
def mastery_repo():
    return AsyncMock()


@pytest.fixture
def svc(session_repo, mastery_repo):
    return LearningVelocityService(session_repo=session_repo, mastery_repo=mastery_repo)


@pytest.mark.asyncio
async def test_velocity_zero_with_no_sessions(svc, session_repo):
    session_repo.list_since.return_value = []
    velocity = await svc.compute_velocity(uuid4())
    assert velocity == 0.0


@pytest.mark.asyncio
async def test_velocity_sums_bloom_gains_over_window(svc, session_repo):
    session_repo.list_since.return_value = [
        make_session(bloom_level="Understand"),  # 5
        make_session(bloom_level="Apply"),        # 8
    ]
    velocity = await svc.compute_velocity(uuid4(), window_days=7)
    assert velocity == round((5 + 8) / 7, 2)


@pytest.mark.asyncio
async def test_velocity_penalises_misconceptions(svc, session_repo):
    session_repo.list_since.return_value = [
        make_session(bloom_level="Apply", misconceptions=["wrong idea"]),  # 8 - 5 = 3
    ]
    velocity = await svc.compute_velocity(uuid4(), window_days=7)
    assert velocity == round(3 / 7, 2)


@pytest.mark.asyncio
async def test_velocity_never_negative_per_session(svc, session_repo):
    session_repo.list_since.return_value = [
        make_session(bloom_level="Remember", misconceptions=["x"]),  # 3 - 5 = -2 -> clamped 0
    ]
    velocity = await svc.compute_velocity(uuid4(), window_days=7)
    assert velocity == 0.0


@pytest.mark.asyncio
async def test_retention_risk_empty_for_fresh_mastery(svc, mastery_repo):
    mastery_repo.list_by_user.return_value = [
        make_mastery(score=90.0, last_updated=datetime.now(UTC)),
    ]
    risks = await svc.compute_retention_risks(uuid4())
    assert risks == []


@pytest.mark.asyncio
async def test_retention_risk_flags_stale_mastery(svc, mastery_repo):
    stale = datetime.now(UTC) - timedelta(days=60)
    mastery_repo.list_by_user.return_value = [
        make_mastery(concept_name="Stale", score=90.0, last_updated=stale),
    ]
    risks = await svc.compute_retention_risks(uuid4())
    assert len(risks) == 1
    assert risks[0].concept_name == "Stale"
    assert 0.0 < risks[0].risk <= 1.0


@pytest.mark.asyncio
async def test_retention_risk_skips_low_scores(svc, mastery_repo):
    stale = datetime.now(UTC) - timedelta(days=60)
    mastery_repo.list_by_user.return_value = [
        make_mastery(score=20.0, last_updated=stale),  # below 30 — not eligible
    ]
    risks = await svc.compute_retention_risks(uuid4())
    assert risks == []


@pytest.mark.asyncio
async def test_retention_risk_sorted_descending(svc, mastery_repo):
    very_stale = datetime.now(UTC) - timedelta(days=120)
    somewhat_stale = datetime.now(UTC) - timedelta(days=40)
    mastery_repo.list_by_user.return_value = [
        make_mastery(concept_name="SomewhatStale", score=90.0, last_updated=somewhat_stale),
        make_mastery(concept_name="VeryStale", score=90.0, last_updated=very_stale),
    ]
    risks = await svc.compute_retention_risks(uuid4())
    assert len(risks) == 2
    assert risks[0].concept_name == "VeryStale"
    assert risks[0].risk >= risks[1].risk
