"""Integration test: the full QuestioningEngine loop over in-memory fakes.

Exercises scheduler → generator → evaluator → confidence-updater → evidence,
mastery, and recall — with no database, proving the service layer composes
end-to-end (it imports no SQLAlchemy).
"""
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from src.application.services.answer_evaluator import AnswerEvaluator
from src.application.services.confidence_updater import ConfidenceUpdater
from src.application.services.evidence_collector import EvidenceCollector
from src.application.services.question_generator import QuestionGenerator
from src.application.services.question_scheduler import QuestionScheduler
from src.application.services.questioning_engine import QuestioningEngine, QuestionOwnershipError
from src.application.services.recall_scheduler import RecallScheduler
from src.domain.entities.learning import MasteryRecord
from tests.fakes import (
    FakeConceptNodeRepository,
    FakeEvidenceRepository,
    FakeLearnerQuestionRepository,
    FakeLearningGapRepository,
    FakeMasteryRepository,
    FakeRecallScheduleRepository,
)

T0 = datetime(2026, 1, 1, tzinfo=UTC)


@pytest.fixture
def rig():
    concepts = FakeConceptNodeRepository()
    mastery = FakeMasteryRepository()
    gaps = FakeLearningGapRepository()
    evidence_repo = FakeEvidenceRepository()
    recall_repo = FakeRecallScheduleRepository()
    questions = FakeLearnerQuestionRepository()

    evidence = EvidenceCollector(evidence_repo)
    recall = RecallScheduler(recall_repo)
    scheduler = QuestionScheduler(
        mastery_repo=mastery, recall_scheduler=recall,
        evidence_collector=evidence, concept_repo=concepts, gap_repo=gaps,
    )
    updater = ConfidenceUpdater(
        evidence_collector=evidence, recall_scheduler=recall,
        mastery_repo=mastery, concept_repo=concepts, gap_repo=gaps,
    )
    engine = QuestioningEngine(
        scheduler=scheduler, generator=QuestionGenerator(),
        evaluator=AnswerEvaluator(), confidence_updater=updater, question_repo=questions,
    )
    return {
        "engine": engine, "concepts": concepts, "mastery": mastery,
        "evidence_repo": evidence_repo, "recall_repo": recall_repo, "questions": questions,
    }


async def _seed_weak_concept(rig, name="Photosynthesis", score=20.0):
    user = uuid4()
    node = rig["concepts"].seed(name)
    rec = MasteryRecord(user_id=user, concept_id=node.id, concept_name=name,
                        score=score, interaction_count=0)
    rig["mastery"].store[(user, node.id)] = rec
    return user, node


async def test_next_question_targets_weak_concept(rig):
    user, node = await _seed_weak_concept(rig)
    q = await rig["engine"].next_question(user, now=T0)
    assert q is not None
    assert q.concept_id == node.id
    assert q.objective == "verify_mastery"
    assert q.status == "asked"


async def test_next_question_reuses_outstanding(rig):
    user, _ = await _seed_weak_concept(rig)
    q1 = await rig["engine"].next_question(user, now=T0)
    q2 = await rig["engine"].next_question(user, now=T0)
    assert q1.id == q2.id   # does not stack a second question


async def test_correct_answer_updates_state_and_confidence(rig):
    user, node = await _seed_weak_concept(rig)
    q = await rig["engine"].next_question(user, now=T0)

    # expected_answer defaults to the concept name, so mentioning it scores full.
    result = await rig["engine"].submit_answer(user, q.id, "Photosynthesis", now=T0)

    assert result.evaluation.is_correct is True
    assert result.evaluation.signal == "correct"
    assert result.confidence_after > 0.0

    # evidence appended
    assert len(rig["evidence_repo"].events) == 1
    # mastery interaction recorded
    rec = rig["mastery"].store[(user, node.id)]
    assert rec.interaction_count == 1
    assert rec.score > 20.0
    # recall schedule created + scheduled forward
    sched = rig["recall_repo"].store[(user, node.id)]
    assert sched.repetitions == 1
    assert sched.next_review_at > T0
    # question consumed
    assert await rig["questions"].next_pending(user) is None


async def test_wrong_answer_records_negative_evidence(rig):
    user, node = await _seed_weak_concept(rig)
    q = await rig["engine"].next_question(user, now=T0)
    result = await rig["engine"].submit_answer(user, q.id, "the sky is blue", now=T0)
    assert result.evaluation.signal == "incorrect"
    assert rig["evidence_repo"].events[0].signal == "incorrect"


async def test_submit_rejects_foreign_question(rig):
    user, _ = await _seed_weak_concept(rig)
    q = await rig["engine"].next_question(user, now=T0)
    with pytest.raises(QuestionOwnershipError):
        await rig["engine"].submit_answer(uuid4(), q.id, "anything", now=T0)


async def test_no_question_when_nothing_to_verify(rig):
    # No mastery records, no gaps, no due recalls → nothing worth asking.
    q = await rig["engine"].next_question(uuid4(), now=T0)
    assert q is None
