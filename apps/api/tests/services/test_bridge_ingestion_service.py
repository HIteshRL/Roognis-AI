"""Unit tests for BridgeIngestionService — external ref -> bridge user -> real engine.

This is the behaviour that used to live inside the ingest route handler; extracting
it into a service made it independently testable (no FastAPI, no DB).
"""
from src.application.services.bridge_ingestion_service import BridgeIngestionService
from src.application.services.confidence_updater import ConfidenceUpdater
from src.application.services.evidence_collector import EvidenceCollector
from src.application.services.recall_scheduler import RecallScheduler
from src.domain.entities.user import User
from tests.fakes import (
    FakeConceptNodeRepository,
    FakeEvidenceRepository,
    FakeLearningGapRepository,
    FakeMasteryRepository,
    FakeRecallScheduleRepository,
)


class FakeUserRepository:
    """Duck-typed to the two methods the service uses (get_by_email + create)."""

    def __init__(self) -> None:
        self.by_email: dict[str, User] = {}
        self.created: list[User] = []

    async def get_by_email(self, email: str) -> User | None:
        return self.by_email.get(email)

    async def create(self, user: User) -> User:
        self.by_email[user.email] = user
        self.created.append(user)
        return user


def _service():
    users = FakeUserRepository()
    concepts = FakeConceptNodeRepository()
    evidence_repo = FakeEvidenceRepository()
    updater = ConfidenceUpdater(
        evidence_collector=EvidenceCollector(evidence_repo),
        recall_scheduler=RecallScheduler(FakeRecallScheduleRepository()),
        mastery_repo=FakeMasteryRepository(),
        concept_repo=concepts,
        gap_repo=FakeLearningGapRepository(),
    )
    svc = BridgeIngestionService(user_repo=users, concept_repo=concepts, confidence_updater=updater)
    return svc, users, evidence_repo


async def test_same_ref_provisions_the_bridge_user_only_once():
    svc, users, _ = _service()
    await svc.ingest(external_ref="demo-1", concept_name="Photosynthesis", signal="correct")
    await svc.ingest(external_ref="demo-1", concept_name="Photosynthesis", signal="incorrect")
    assert len(users.created) == 1
    assert users.created[0].email == "bridge+demo-1@bridge.local"
    assert users.created[0].password_hash == "!bridge-no-login"   # unusable → cannot authenticate


async def test_evidence_is_recorded_under_the_bridge_user():
    svc, users, evidence_repo = _service()
    ev = await svc.ingest(external_ref="s2", concept_name="Fractions", signal="correct", weight=0.8)
    assert ev.signal == "correct"
    assert ev.user_id == users.created[0].id
    assert ev.concept_name == "Fractions"
    assert len(evidence_repo.events) == 1
    assert ev.confidence_after > 0.0


async def test_distinct_refs_map_to_distinct_users():
    svc, users, _ = _service()
    await svc.ingest(external_ref="a", concept_name="X", signal="correct")
    await svc.ingest(external_ref="b", concept_name="X", signal="correct")
    assert len({u.id for u in users.created}) == 2
