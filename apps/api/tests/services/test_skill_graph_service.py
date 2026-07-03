"""Unit tests for SkillGraphService."""
import pytest
from uuid import uuid4

from src.application.services.skill_graph_service import SkillGraphService
from src.domain.entities.learning import LearningSession, MasteryRecord


def _make_mastery(concept_name="Algebra", score=70.0) -> MasteryRecord:
    r = MasteryRecord.__new__(MasteryRecord)
    r.id = uuid4()
    r.user_id = uuid4()
    r.concept_id = uuid4()
    r.concept_name = concept_name
    r.score = score
    r.interaction_count = 5
    return r


def _make_session(bloom="Apply", concept="Algebra") -> LearningSession:
    s = LearningSession.__new__(LearningSession)
    s.id = uuid4()
    s.user_id = uuid4()
    s.question = "test"
    s.ai_response = "test"
    s.primary_concept = concept
    s.concepts_discussed = []
    s.bloom_level = bloom
    s.skills = []
    s.intent = "unknown"
    return s


@pytest.fixture
def svc():
    return SkillGraphService()


def test_derive_skills_remember(svc):
    skills = svc.derive_skills_for_bloom("Remember")
    assert "Knowledge Recall" in skills


def test_derive_skills_apply(svc):
    skills = svc.derive_skills_for_bloom("Apply")
    assert "Problem Solving" in skills


def test_derive_skills_unknown_bloom(svc):
    skills = svc.derive_skills_for_bloom("NonExistent")
    assert skills == []


def test_build_profile_with_sessions(svc):
    records = [_make_mastery("Algebra", 80)]
    sessions = [_make_session("Apply", "Algebra")]
    profile = svc.build_student_skill_profile(records, sessions)
    assert "Problem Solving" in profile
    assert profile["Problem Solving"] == 80.0


def test_build_profile_empty_sessions_uses_score_heuristic(svc):
    records = [_make_mastery("Trigonometry", 90)]
    profile = svc.build_student_skill_profile(records, [])
    # score >= 85 → "Evaluate" level skills
    assert len(profile) > 0


def test_top_skills_sorted(svc):
    profile = {"Skill A": 90.0, "Skill B": 50.0, "Skill C": 75.0}
    top = svc.top_skills(profile, n=2)
    assert top[0]["skill"] == "Skill A"
    assert top[1]["skill"] == "Skill C"


def test_bloom_distribution(svc):
    sessions = [
        _make_session("Apply"),
        _make_session("Apply"),
        _make_session("Analyze"),
    ]
    dist = svc.categorize_bloom_distribution(sessions)
    assert dist["Apply"] == 2
    assert dist["Analyze"] == 1
    assert dist["Remember"] == 0
