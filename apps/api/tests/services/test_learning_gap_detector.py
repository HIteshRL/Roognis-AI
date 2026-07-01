"""Unit tests for LearningGapDetector and LearningGap domain logic."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from src.domain.entities.learning import LearningGap
from src.application.services.learning_gap_detector import LearningGapDetector
from src.application.dtos.learning import ConceptExtractionResult


def make_gap(**kwargs) -> LearningGap:
    defaults = dict(
        user_id=uuid4(),
        concept_id=uuid4(),
        concept_name="Test Concept",
        occurrence_count=1,
    )
    defaults.update(kwargs)
    return LearningGap(**defaults)


# ── LearningGap domain logic ──────────────────────────────────────────────────

def test_gap_initial_severity_is_medium():
    g = make_gap()
    assert g.severity == "medium"


def test_gap_increment_to_medium_at_2():
    g = make_gap(occurrence_count=1)
    g.increment()
    assert g.occurrence_count == 2
    assert g.severity == "medium"
    assert g.confidence == "medium"


def test_gap_increment_to_high_at_3():
    g = make_gap(occurrence_count=2)
    g.increment()
    assert g.occurrence_count == 3
    assert g.severity == "high"
    assert g.confidence == "high"


def test_gap_increment_to_critical_at_5():
    g = make_gap(occurrence_count=4)
    g.increment()
    assert g.occurrence_count == 5
    assert g.severity == "critical"


def test_gap_resolve():
    g = make_gap()
    assert not g.is_resolved
    g.resolve()
    assert g.is_resolved


# ── LearningGapDetector service tests ────────────────────────────────────────

@pytest.fixture
def gap_repo():
    repo = AsyncMock()
    return repo


@pytest.fixture
def concept_repo():
    repo = AsyncMock()
    return repo


@pytest.fixture
def detector(gap_repo, concept_repo):
    return LearningGapDetector(gap_repo=gap_repo, concept_repo=concept_repo)


@pytest.mark.asyncio
async def test_no_gaps_when_no_misconceptions(detector, gap_repo, concept_repo):
    extraction = ConceptExtractionResult(
        primary_concept="Algebra",
        bloom_level="Apply",
        misconceptions=[],
    )
    result = await detector.process_extraction(uuid4(), extraction)
    assert result == []
    gap_repo.get_or_create.assert_not_called()


@pytest.mark.asyncio
async def test_gap_created_for_misconception(detector, gap_repo, concept_repo):
    node_id = uuid4()
    mock_node = MagicMock()
    mock_node.id = node_id
    mock_node.name = "Newton's Laws"
    concept_repo.get_or_create.return_value = mock_node

    mock_gap = make_gap(
        concept_id=node_id, concept_name="Newton's Laws", occurrence_count=1
    )
    gap_repo.get_or_create.return_value = mock_gap
    gap_repo.update.return_value = mock_gap

    extraction = ConceptExtractionResult(
        primary_concept="Newton's Laws",
        bloom_level="Understand",
        misconceptions=["Confused inertia with momentum"],
    )
    result = await detector.process_extraction(uuid4(), extraction)
    assert len(result) == 1
    gap_repo.get_or_create.assert_called_once()


@pytest.mark.asyncio
async def test_multiple_misconceptions_create_multiple_gaps(detector, gap_repo, concept_repo):
    mock_node = MagicMock()
    mock_node.id = uuid4()
    mock_node.name = "Gravity"
    concept_repo.get_or_create.return_value = mock_node

    mock_gap = make_gap(concept_id=mock_node.id, concept_name="Gravity")
    gap_repo.get_or_create.return_value = mock_gap
    gap_repo.update.return_value = mock_gap

    extraction = ConceptExtractionResult(
        primary_concept="Gravity",
        bloom_level="Analyze",
        misconceptions=["Thinks gravity acts upward", "Confuses weight and mass"],
    )
    result = await detector.process_extraction(uuid4(), extraction)
    assert len(result) == 2
    assert gap_repo.get_or_create.call_count == 2
