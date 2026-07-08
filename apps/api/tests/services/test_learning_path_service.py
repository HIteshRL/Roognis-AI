"""Unit tests for LearningPathService."""
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.application.services.learning_path_service import LearningPathService, _frontier_reason
from src.domain.entities.learning import ConceptNode, MasteryRecord


def _make_node(name="Concept A", subject="Math", grade="10") -> ConceptNode:
    n = ConceptNode.__new__(ConceptNode)
    n.id = uuid4()
    n.name = name
    n.subject = subject
    n.grade = grade
    n.chapter = None
    n.description = None
    n.bloom_level = "Understand"
    n.difficulty = "medium"
    return n


def _make_mastery(concept_id, score=50.0) -> MasteryRecord:
    r = MasteryRecord.__new__(MasteryRecord)
    r.id = uuid4()
    r.user_id = uuid4()
    r.concept_id = concept_id
    r.concept_name = "Test Concept"
    r.score = score
    r.interaction_count = 3
    return r


@pytest.fixture
def mock_profile():
    p = MagicMock()
    p.grade = "10"
    p.subjects = ["Math"]
    return p


@pytest.fixture
def svc():
    graph = MagicMock()
    graph.get_all_prerequisites = AsyncMock(return_value=[])
    graph.learning_order = AsyncMock(side_effect=lambda ids: ids)
    graph.list_by_subject = AsyncMock(return_value=[])
    graph.readiness_for = AsyncMock(return_value=1.0)
    mastery_repo = MagicMock()
    mastery_repo.list_by_user = AsyncMock(return_value=[])
    profile_repo = MagicMock()
    profile_repo.get_by_user_id = AsyncMock(return_value=None)
    return LearningPathService(graph=graph, mastery_repo=mastery_repo, profile_repo=profile_repo)


@pytest.mark.asyncio
async def test_get_frontier_no_profile_returns_empty(svc):
    result = await svc.get_frontier(uuid4())
    assert result == []


@pytest.mark.asyncio
async def test_get_frontier_with_profile_and_nodes(svc, mock_profile):
    node = _make_node()
    svc._profiles.get_by_user_id = AsyncMock(return_value=mock_profile)
    svc._graph.list_by_subject = AsyncMock(return_value=[node])
    svc._graph.readiness_for = AsyncMock(return_value=0.8)
    svc._mastery.list_by_user = AsyncMock(return_value=[])

    result = await svc.get_frontier(uuid4())
    assert len(result) == 1
    assert result[0].concept_name == node.name


@pytest.mark.asyncio
async def test_get_frontier_skips_mastered_concepts(svc, mock_profile):
    node = _make_node()
    mastery = _make_mastery(node.id, score=90.0)
    svc._profiles.get_by_user_id = AsyncMock(return_value=mock_profile)
    svc._graph.list_by_subject = AsyncMock(return_value=[node])
    svc._mastery.list_by_user = AsyncMock(return_value=[mastery])

    result = await svc.get_frontier(uuid4())
    assert result == []


@pytest.mark.asyncio
async def test_get_frontier_skips_low_readiness(svc, mock_profile):
    node = _make_node()
    svc._profiles.get_by_user_id = AsyncMock(return_value=mock_profile)
    svc._graph.list_by_subject = AsyncMock(return_value=[node])
    svc._graph.readiness_for = AsyncMock(return_value=0.3)  # below threshold
    svc._mastery.list_by_user = AsyncMock(return_value=[])

    result = await svc.get_frontier(uuid4())
    assert result == []


@pytest.mark.asyncio
async def test_path_to_concept_returns_ordered_prerequisites(svc, mock_profile):
    prereq = _make_node("Prereq A")
    target_id = uuid4()
    svc._profiles.get_by_user_id = AsyncMock(return_value=mock_profile)
    svc._graph.get_all_prerequisites = AsyncMock(return_value=[prereq])
    svc._mastery.list_by_user = AsyncMock(return_value=[])  # nothing mastered
    svc._graph.learning_order = AsyncMock(return_value=[prereq.id])

    result = await svc.path_to_concept(uuid4(), target_id)
    assert len(result) == 1
    assert result[0].name == "Prereq A"


@pytest.mark.asyncio
async def test_path_to_concept_excludes_already_mastered(svc):
    prereq = _make_node("Already Mastered")
    mastery = _make_mastery(prereq.id, score=90.0)
    svc._graph.get_all_prerequisites = AsyncMock(return_value=[prereq])
    svc._mastery.list_by_user = AsyncMock(return_value=[mastery])

    result = await svc.path_to_concept(uuid4(), uuid4())
    assert result == []


@pytest.mark.asyncio
async def test_curriculum_coverage_empty_when_no_profile(svc):
    result = await svc.curriculum_coverage(uuid4())
    assert result == {}


def test_frontier_reason_all_prereqs_new():
    assert "All prerequisites mastered" in _frontier_reason(1.0, 0.0)


def test_frontier_reason_partial():
    reason = _frontier_reason(0.75, 0.0)
    assert "75%" in reason
