"""Unit tests for KnowledgeGraphService."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from src.application.services.knowledge_graph_service import KnowledgeGraphService
from src.domain.entities.learning import ConceptEdge, ConceptNode


def make_node(name: str = "Test", **kwargs) -> ConceptNode:
    return ConceptNode(name=name, **kwargs)


@pytest.fixture
def node_repo():
    return AsyncMock()


@pytest.fixture
def edge_repo():
    return AsyncMock()


@pytest.fixture
def svc(node_repo, edge_repo):
    return KnowledgeGraphService(node_repo=node_repo, edge_repo=edge_repo)


@pytest.mark.asyncio
async def test_get_or_create_node_delegates(svc, node_repo):
    expected = make_node("Algebra")
    node_repo.get_or_create.return_value = expected
    result = await svc.get_or_create_node("Algebra", subject="Math", grade="9")
    node_repo.get_or_create.assert_called_once_with("Algebra", "Math", "9", None)
    assert result.name == "Algebra"


@pytest.mark.asyncio
async def test_add_prerequisite_creates_edge_when_absent(svc, edge_repo):
    edge_repo.exists.return_value = False
    source_id = uuid4()
    target_id = uuid4()
    mock_edge = ConceptEdge(source_id=source_id, target_id=target_id)
    edge_repo.create.return_value = mock_edge

    result = await svc.add_prerequisite(source_id, target_id)
    edge_repo.create.assert_called_once()
    assert result is not None


@pytest.mark.asyncio
async def test_add_prerequisite_skips_when_exists(svc, edge_repo):
    edge_repo.exists.return_value = True
    result = await svc.add_prerequisite(uuid4(), uuid4())
    edge_repo.create.assert_not_called()
    assert result is None


@pytest.mark.asyncio
async def test_readiness_1_when_no_prereqs(svc, edge_repo):
    edge_repo.get_prerequisites.return_value = []
    score = await svc.readiness_for(uuid4(), {})
    assert score == 1.0


@pytest.mark.asyncio
async def test_readiness_partial_with_unmastered_prereqs(svc, edge_repo):
    p1_id = uuid4()
    p2_id = uuid4()
    p1 = make_node("Prereq1")
    p1.id = p1_id
    p2 = make_node("Prereq2")
    p2.id = p2_id
    edge_repo.get_prerequisites.return_value = [p1, p2]

    # Only p1 is mastered (≥70)
    mastery_map = {p1_id: 75.0, p2_id: 40.0}
    score = await svc.readiness_for(uuid4(), mastery_map)
    assert score == 0.5


@pytest.mark.asyncio
async def test_readiness_full_when_all_prereqs_mastered(svc, edge_repo):
    p_id = uuid4()
    p = make_node("Prereq")
    p.id = p_id
    edge_repo.get_prerequisites.return_value = [p]
    mastery_map = {p_id: 90.0}
    score = await svc.readiness_for(uuid4(), mastery_map)
    assert score == 1.0


@pytest.mark.asyncio
async def test_readiness_zero_when_no_mastery_data(svc, edge_repo):
    p_id = uuid4()
    p = make_node("Prereq")
    p.id = p_id
    edge_repo.get_prerequisites.return_value = [p]
    score = await svc.readiness_for(uuid4(), {})
    assert score == 0.0
