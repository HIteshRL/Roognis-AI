"""Tests for PreferenceInferenceEngine over an in-memory preference repository."""
from uuid import uuid4

from src.application.services.preference_inference_engine import PreferenceInferenceEngine
from tests.fakes import FakeLearnerPreferenceRepository


def _engine() -> PreferenceInferenceEngine:
    return PreferenceInferenceEngine(preference_repo=FakeLearnerPreferenceRepository())


async def test_problem_solving_infers_worked_examples_and_steps():
    e = _engine()
    user = uuid4()
    updated = await e.infer_from_interaction(user, intent="problem_solving")
    dims = {p.dimension for p in updated}
    assert "worked_examples" in dims
    assert "step_by_step" in dims


async def test_single_interaction_is_not_yet_reliable():
    e = _engine()
    user = uuid4()
    await e.infer_from_interaction(user, intent="problem_solving")
    reliable = await e.reliable_preferences(user)
    assert reliable == []   # one observation is not enough to be reliable


async def test_repeated_interactions_become_reliable():
    e = _engine()
    user = uuid4()
    for _ in range(4):
        await e.infer_from_interaction(user, intent="problem_solving")
    reliable = await e.reliable_preferences(user)
    dims = {p.dimension for p in reliable}
    assert "step_by_step" in dims
    assert all(p.is_reliable for p in reliable)


async def test_misconception_pushes_step_by_step_and_short():
    e = _engine()
    user = uuid4()
    updated = await e.infer_from_interaction(
        user, intent="concept_explanation", bloom_level="Understand", had_misconception=True
    )
    dims = {p.dimension for p in updated}
    assert "step_by_step" in dims
    assert "short" in dims


async def test_unknown_dimension_is_ignored():
    e = _engine()
    user = uuid4()
    result = await e.observe(user, "not_a_dimension", 0.9)
    assert result is None
