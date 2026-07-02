"""Integration tests for /api/v1/student endpoints."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from fastapi.testclient import TestClient

from src.application import interfaces
from src.application.interfaces import dependencies
from src.main import app


def _mock_user():
    user = MagicMock()
    user.id = str(uuid4())
    user.email = "student@test.com"
    return user


def _make_profile(user_id):
    from src.domain.entities.learning import BehavioralSignals, StudentProfile
    from datetime import datetime, UTC
    p = StudentProfile.__new__(StudentProfile)
    p.id = uuid4()
    p.user_id = user_id
    p.institution = "Test School"
    p.grade = "10"
    p.subjects = ["Math", "Science"]
    p.current_chapter = "Chapter 1"
    p.learning_velocity = 0.5
    p.confidence_score = 0.6
    p.behavioral_signals = BehavioralSignals()
    p.last_active = datetime.now(UTC)
    p.created_at = datetime.now(UTC)
    p.updated_at = datetime.now(UTC)
    return p


@pytest.fixture(autouse=True)
def override_deps():
    user = _mock_user()
    user_uuid = uuid4()

    mock_profile_svc = AsyncMock()
    mock_session_svc = AsyncMock()
    mock_mastery_engine = AsyncMock()
    mock_gap_detector = AsyncMock()
    mock_recommendation_engine = AsyncMock()
    mock_analytics_svc = AsyncMock()

    profile = _make_profile(user_uuid)
    mock_profile_svc.get_or_create.return_value = profile
    mock_profile_svc.update.return_value = profile
    mock_session_svc.list_sessions.return_value = ([], 0)
    mock_mastery_engine.get_all.return_value = []
    mock_gap_detector.list_gaps.return_value = []
    mock_recommendation_engine.recommend.return_value = []

    from src.application.dtos.learning import LearningAnalyticsResponse
    mock_analytics_svc.get_analytics.return_value = LearningAnalyticsResponse(
        user_id=user_uuid,
        total_sessions=0,
        total_concepts_encountered=0,
        average_mastery=0.0,
        mastered_count=0,
        developing_count=0,
        emerging_count=0,
        not_started_count=0,
        active_gaps=0,
        critical_gaps=0,
        recent_bloom_levels={},
        recent_concepts=[],
    )

    app.dependency_overrides[dependencies.get_current_user] = lambda: user
    app.dependency_overrides[dependencies.get_student_profile_service] = lambda: mock_profile_svc
    app.dependency_overrides[dependencies.get_session_memory_service] = lambda: mock_session_svc
    app.dependency_overrides[dependencies.get_mastery_engine] = lambda: mock_mastery_engine
    app.dependency_overrides[dependencies.get_learning_gap_detector] = lambda: mock_gap_detector
    app.dependency_overrides[dependencies.get_next_best_topic_engine] = lambda: mock_recommendation_engine
    app.dependency_overrides[dependencies.get_learning_analytics_service] = lambda: mock_analytics_svc

    yield

    app.dependency_overrides.clear()


@pytest.fixture
def client():
    return TestClient(app)


def test_get_profile_returns_200(client):
    resp = client.get("/api/v1/student/profile")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "grade" in data["data"]


def test_update_profile_returns_200(client):
    resp = client.post(
        "/api/v1/student/profile",
        json={"grade": "11", "subjects": ["Physics"]},
    )
    assert resp.status_code == 200


def test_list_sessions_returns_200(client):
    resp = client.get("/api/v1/student/sessions")
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["data"] == []


def test_get_mastery_returns_200(client):
    resp = client.get("/api/v1/student/mastery")
    assert resp.status_code == 200


def test_get_gaps_returns_200(client):
    resp = client.get("/api/v1/student/gaps")
    assert resp.status_code == 200


def test_get_recommendations_returns_200(client):
    resp = client.get("/api/v1/student/recommendations")
    assert resp.status_code == 200


def test_get_analytics_returns_200(client):
    resp = client.get("/api/v1/student/analytics")
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["total_sessions"] == 0
