"""Unit tests for LearnerBehaviorService — Phase 0.3 behavioral analysis."""
import pytest
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

from src.application.services.learner_behavior_service import LearnerBehaviorService
from src.domain.entities.learning import LearningGap, LearningSession, MasteryRecord


def _session(
    bloom="Understand",
    difficulty="medium",
    misconceptions=None,
    duration_ms=5000,
    subject=None,
    primary_concept=None,
    days_ago=0,
) -> LearningSession:
    return LearningSession(
        user_id=uuid4(),
        question="test",
        ai_response="test",
        bloom_level=bloom,
        difficulty_level=difficulty,
        misconceptions=misconceptions or [],
        duration_ms=duration_ms,
        subject=subject,
        primary_concept=primary_concept,
        created_at=datetime.now(UTC) - timedelta(days=days_ago),
    )


def _mastery(concept_name="Concept", score=50.0) -> MasteryRecord:
    return MasteryRecord(user_id=uuid4(), concept_id=uuid4(), concept_name=concept_name, score=score)


def _gap(severity="medium", is_resolved=False) -> LearningGap:
    g = LearningGap(user_id=uuid4(), concept_id=uuid4(), concept_name="Test")
    g.severity = severity
    g.is_resolved = is_resolved
    return g


@pytest.fixture
def repos():
    return AsyncMock(), AsyncMock(), AsyncMock()


@pytest.fixture
def svc(repos):
    session_repo, mastery_repo, gap_repo = repos
    return LearnerBehaviorService(session_repo=session_repo, mastery_repo=mastery_repo, gap_repo=gap_repo)


@pytest.mark.asyncio
async def test_empty_sessions_returns_defaults(svc, repos):
    session_repo, mastery_repo, gap_repo = repos
    session_repo.list_since.return_value = []
    session_repo.count_by_user.return_value = 0
    mastery_repo.list_by_user.return_value = []
    gap_repo.list_by_user.return_value = []

    signals = await svc.compute(uuid4())
    assert signals.total_sessions == 0
    assert signals.preferred_bloom_level is None
    assert signals.response_pattern == "unknown"


@pytest.mark.asyncio
async def test_preferred_bloom_is_mode(svc, repos):
    session_repo, mastery_repo, gap_repo = repos
    sessions = [
        _session(bloom="Apply"),
        _session(bloom="Apply"),
        _session(bloom="Apply"),
        _session(bloom="Remember"),
    ]
    session_repo.list_since.return_value = sessions
    session_repo.count_by_user.return_value = 4
    mastery_repo.list_by_user.return_value = []
    gap_repo.list_by_user.return_value = []

    signals = await svc.compute(uuid4())
    assert signals.preferred_bloom_level == "Apply"


@pytest.mark.asyncio
async def test_struggle_bloom_from_misconceptions(svc, repos):
    session_repo, mastery_repo, gap_repo = repos
    sessions = [
        _session(bloom="Analyze", misconceptions=["wrong"]),
        _session(bloom="Analyze", misconceptions=["also wrong"]),
        _session(bloom="Apply"),
    ]
    session_repo.list_since.return_value = sessions
    session_repo.count_by_user.return_value = 3
    mastery_repo.list_by_user.return_value = []
    gap_repo.list_by_user.return_value = []

    signals = await svc.compute(uuid4())
    assert signals.struggle_bloom_level == "Analyze"


@pytest.mark.asyncio
async def test_avg_session_duration(svc, repos):
    session_repo, mastery_repo, gap_repo = repos
    sessions = [_session(duration_ms=10000), _session(duration_ms=20000)]
    session_repo.list_since.return_value = sessions
    session_repo.count_by_user.return_value = 2
    mastery_repo.list_by_user.return_value = []
    gap_repo.list_by_user.return_value = []

    signals = await svc.compute(uuid4())
    assert signals.avg_session_duration_ms == 15000


@pytest.mark.asyncio
async def test_sessions_per_day(svc, repos):
    session_repo, mastery_repo, gap_repo = repos
    sessions = [_session(days_ago=i) for i in range(7)]
    session_repo.list_since.return_value = sessions
    session_repo.count_by_user.return_value = 7
    mastery_repo.list_by_user.return_value = []
    gap_repo.list_by_user.return_value = []

    signals = await svc.compute(uuid4())
    assert signals.sessions_per_day > 0


@pytest.mark.asyncio
async def test_complexity_trend_rising(svc, repos):
    session_repo, mastery_repo, gap_repo = repos
    sessions = [
        _session(bloom="Analyze", days_ago=0),
        _session(bloom="Evaluate", days_ago=1),
        _session(bloom="Remember", days_ago=5),
        _session(bloom="Understand", days_ago=6),
    ]
    session_repo.list_since.return_value = sessions
    session_repo.count_by_user.return_value = 4
    mastery_repo.list_by_user.return_value = []
    gap_repo.list_by_user.return_value = []

    signals = await svc.compute(uuid4())
    assert signals.question_complexity_trend == "rising"


@pytest.mark.asyncio
async def test_dominant_subject(svc, repos):
    session_repo, mastery_repo, gap_repo = repos
    sessions = [
        _session(subject="Math"),
        _session(subject="Math"),
        _session(subject="Science"),
    ]
    session_repo.list_since.return_value = sessions
    session_repo.count_by_user.return_value = 3
    mastery_repo.list_by_user.return_value = []
    gap_repo.list_by_user.return_value = []

    signals = await svc.compute(uuid4())
    assert signals.dominant_subject == "Math"


@pytest.mark.asyncio
async def test_strengths_from_mastery(svc, repos):
    session_repo, mastery_repo, gap_repo = repos
    session_repo.list_since.return_value = [_session()]
    session_repo.count_by_user.return_value = 1
    mastery_repo.list_by_user.return_value = [
        _mastery("Algebra", 95.0),
        _mastery("Geometry", 90.0),
        _mastery("Fractions", 40.0),
    ]
    gap_repo.list_by_user.return_value = []

    signals = await svc.compute(uuid4())
    assert "Algebra" in signals.strengths
    assert "Geometry" in signals.strengths
    assert "Fractions" not in signals.strengths


@pytest.mark.asyncio
async def test_engagement_streak(svc, repos):
    session_repo, mastery_repo, gap_repo = repos
    now = datetime.now(UTC)
    sessions = [_session(days_ago=i) for i in range(5)]
    session_repo.list_since.return_value = sessions
    session_repo.count_by_user.return_value = 5
    mastery_repo.list_by_user.return_value = []
    gap_repo.list_by_user.return_value = []

    signals = await svc.compute(uuid4())
    assert signals.engagement_streak >= 4


@pytest.mark.asyncio
async def test_response_pattern_procedural(svc, repos):
    session_repo, mastery_repo, gap_repo = repos
    sessions = [
        _session(bloom="Remember"),
        _session(bloom="Understand"),
        _session(bloom="Apply"),
        _session(bloom="Remember"),
    ]
    session_repo.list_since.return_value = sessions
    session_repo.count_by_user.return_value = 4
    mastery_repo.list_by_user.return_value = []
    gap_repo.list_by_user.return_value = []

    signals = await svc.compute(uuid4())
    assert signals.response_pattern == "procedural"


@pytest.mark.asyncio
async def test_response_pattern_conceptual(svc, repos):
    session_repo, mastery_repo, gap_repo = repos
    sessions = [
        _session(bloom="Analyze"),
        _session(bloom="Evaluate"),
        _session(bloom="Create"),
        _session(bloom="Analyze"),
    ]
    session_repo.list_since.return_value = sessions
    session_repo.count_by_user.return_value = 4
    mastery_repo.list_by_user.return_value = []
    gap_repo.list_by_user.return_value = []

    signals = await svc.compute(uuid4())
    assert signals.response_pattern == "conceptual"


@pytest.mark.asyncio
async def test_recent_topics_unique_and_ordered(svc, repos):
    session_repo, mastery_repo, gap_repo = repos
    sessions = [
        _session(primary_concept="A", days_ago=0),
        _session(primary_concept="A", days_ago=1),
        _session(primary_concept="B", days_ago=2),
        _session(primary_concept="C", days_ago=3),
    ]
    session_repo.list_since.return_value = sessions
    session_repo.count_by_user.return_value = 4
    mastery_repo.list_by_user.return_value = []
    gap_repo.list_by_user.return_value = []

    signals = await svc.compute(uuid4())
    assert signals.recent_topics == ["A", "B", "C"]


@pytest.mark.asyncio
async def test_misconception_count_from_unresolved_gaps(svc, repos):
    session_repo, mastery_repo, gap_repo = repos
    session_repo.list_since.return_value = [_session()]
    session_repo.count_by_user.return_value = 1
    mastery_repo.list_by_user.return_value = []
    gap_repo.list_by_user.return_value = [
        _gap(is_resolved=False),
        _gap(is_resolved=False),
        _gap(is_resolved=True),
    ]

    signals = await svc.compute(uuid4())
    assert signals.total_misconceptions == 2
