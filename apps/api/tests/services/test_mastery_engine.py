"""Unit tests for MasteryEngine and MasteryRecord domain logic."""
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.application.services.mastery_engine import MasteryEngine
from src.domain.entities.learning import MasteryRecord

# ── MasteryRecord domain tests ────────────────────────────────────────────────

def make_record(**kwargs) -> MasteryRecord:
    defaults = dict(user_id=uuid4(), concept_id=uuid4(), concept_name="Test Concept")
    defaults.update(kwargs)
    return MasteryRecord(**defaults)


def test_label_not_started():
    r = make_record(score=0.0)
    assert r.label == "not_started"


def test_label_emerging():
    r = make_record(score=30.0)
    assert r.label == "emerging"


def test_label_developing():
    r = make_record(score=60.0)
    assert r.label == "developing"


def test_label_mastered():
    r = make_record(score=85.0)
    assert r.label == "mastered"


def test_apply_interaction_increases_score():
    r = make_record(score=0.0)
    r.apply_interaction("Understand", has_misconception=False)
    assert r.score > 0.0
    assert r.interaction_count == 1


def test_apply_interaction_misconception_penalises():
    r1 = make_record(score=20.0)
    r2 = make_record(score=20.0)
    r1.apply_interaction("Apply", has_misconception=False)
    r2.apply_interaction("Apply", has_misconception=True)
    assert r1.score > r2.score


def test_apply_interaction_score_never_exceeds_100():
    r = make_record(score=99.0)
    r.apply_interaction("Create", has_misconception=False)
    assert r.score <= 100.0


def test_apply_interaction_score_never_below_zero():
    r = make_record(score=0.0)
    r.apply_interaction("Remember", has_misconception=True)
    assert r.score >= 0.0


def test_higher_bloom_gives_more_gain():
    r_low = make_record(score=0.0)
    r_high = make_record(score=0.0)
    r_low.apply_interaction("Remember", has_misconception=False)
    r_high.apply_interaction("Create", has_misconception=False)
    assert r_high.score > r_low.score


def test_ema_smoothing_prevents_single_spike():
    r = make_record(score=0.0)
    for _ in range(5):
        r.apply_interaction("Create", has_misconception=False)
    assert r.score < 100.0


# ── MasteryEngine service tests ───────────────────────────────────────────────

@pytest.fixture
def mastery_repo():
    repo = AsyncMock()
    repo.get_or_create = AsyncMock()
    repo.update = AsyncMock()
    return repo


@pytest.fixture
def concept_repo():
    repo = AsyncMock()
    repo.get_or_create = AsyncMock()
    return repo


@pytest.fixture
def engine(mastery_repo, concept_repo):
    return MasteryEngine(mastery_repo=mastery_repo, concept_repo=concept_repo)


@pytest.mark.asyncio
async def test_update_from_extraction_creates_records(engine, mastery_repo, concept_repo):
    from src.application.dtos.learning import ConceptExtractionResult

    user_id = uuid4()
    node_id = uuid4()

    mock_node = MagicMock()
    mock_node.id = node_id
    mock_node.name = "Photosynthesis"
    concept_repo.get_or_create.return_value = mock_node

    mock_record = make_record(user_id=user_id, concept_id=node_id, concept_name="Photosynthesis")
    mastery_repo.get_or_create.return_value = mock_record
    mastery_repo.update.return_value = mock_record

    extraction = ConceptExtractionResult(
        primary_concept="Photosynthesis",
        secondary_concepts=["Chlorophyll"],
        bloom_level="Understand",
    )
    await engine.update_from_extraction(user_id, extraction, subject="Biology", grade="9")

    # Called once for primary + once for secondary = 2 concept lookups
    assert concept_repo.get_or_create.call_count == 2
    assert mastery_repo.update.call_count == 2


@pytest.mark.asyncio
async def test_update_from_extraction_skips_empty_concepts(engine, concept_repo):
    from src.application.dtos.learning import ConceptExtractionResult

    extraction = ConceptExtractionResult(
        primary_concept="",
        secondary_concepts=["", "  "],
        bloom_level="Remember",
    )
    await engine.update_from_extraction(uuid4(), extraction)
    concept_repo.get_or_create.assert_not_called()
