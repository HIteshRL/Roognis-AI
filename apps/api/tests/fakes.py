"""In-memory fake repositories for Learner Intelligence service/integration tests.

These implement the domain repository ABCs with dict-backed storage so the full
service layer can be exercised without a database (the service layer never
imports SQLAlchemy — only the infrastructure repos do).
"""
from datetime import datetime
from uuid import UUID, uuid4

from src.domain.entities.learning import ConceptNode, LearningGap, MasteryRecord
from src.domain.entities.question import (
    GeneratedQuestion,
    LearnerEvidence,
    LearnerPreference,
    RecallSchedule,
)
from src.domain.repositories.learning_repository import (
    AbstractConceptNodeRepository,
    AbstractLearningGapRepository,
    AbstractMasteryRepository,
)
from src.domain.repositories.question_repository import (
    AbstractEvidenceRepository,
    AbstractLearnerPreferenceRepository,
    AbstractLearnerQuestionRepository,
    AbstractRecallScheduleRepository,
)


class FakeEvidenceRepository(AbstractEvidenceRepository):
    def __init__(self) -> None:
        self.events: list[LearnerEvidence] = []

    async def add(self, evidence: LearnerEvidence) -> LearnerEvidence:
        self.events.append(evidence)
        return evidence

    async def list_by_user(self, user_id: UUID, limit: int = 100) -> list[LearnerEvidence]:
        rows = [e for e in self.events if e.user_id == user_id]
        return list(reversed(rows))[:limit]

    async def list_by_concept(
        self, user_id: UUID, concept_id: UUID, limit: int = 50
    ) -> list[LearnerEvidence]:
        rows = [e for e in self.events if e.user_id == user_id and e.concept_id == concept_id]
        return list(reversed(rows))[:limit]

    async def count_by_concept(self, user_id: UUID, concept_id: UUID) -> int:
        return len([e for e in self.events if e.user_id == user_id and e.concept_id == concept_id])


class FakeLearnerQuestionRepository(AbstractLearnerQuestionRepository):
    def __init__(self) -> None:
        self.store: dict[UUID, GeneratedQuestion] = {}

    async def create(self, question: GeneratedQuestion) -> GeneratedQuestion:
        self.store[question.id] = question
        return question

    async def update(self, question: GeneratedQuestion) -> GeneratedQuestion:
        self.store[question.id] = question
        return question

    async def get_by_id(self, question_id: UUID) -> GeneratedQuestion | None:
        return self.store.get(question_id)

    async def list_by_user(
        self, user_id: UUID, status: str | None = None, limit: int = 20
    ) -> list[GeneratedQuestion]:
        rows = [q for q in self.store.values() if q.user_id == user_id]
        if status:
            rows = [q for q in rows if q.status == status]
        rows.sort(key=lambda q: q.created_at, reverse=True)
        return rows[:limit]

    async def next_pending(self, user_id: UUID) -> GeneratedQuestion | None:
        rows = [
            q for q in self.store.values()
            if q.user_id == user_id and q.status in ("pending", "asked")
        ]
        rows.sort(key=lambda q: q.created_at)
        return rows[0] if rows else None


class FakeRecallScheduleRepository(AbstractRecallScheduleRepository):
    def __init__(self) -> None:
        self.store: dict[tuple[UUID, UUID], RecallSchedule] = {}

    async def get_or_create(
        self, user_id: UUID, concept_id: UUID, concept_name: str
    ) -> RecallSchedule:
        key = (user_id, concept_id)
        if key not in self.store:
            self.store[key] = RecallSchedule(
                user_id=user_id, concept_id=concept_id, concept_name=concept_name
            )
        return self.store[key]

    async def update(self, schedule: RecallSchedule) -> RecallSchedule:
        self.store[(schedule.user_id, schedule.concept_id)] = schedule
        return schedule

    async def get_by_concept(self, user_id: UUID, concept_id: UUID) -> RecallSchedule | None:
        return self.store.get((user_id, concept_id))

    async def list_by_user(self, user_id: UUID) -> list[RecallSchedule]:
        rows = [s for s in self.store.values() if s.user_id == user_id]
        rows.sort(key=lambda s: s.next_review_at)
        return rows

    async def list_due(self, user_id: UUID, now: datetime) -> list[RecallSchedule]:
        rows = [
            s for s in self.store.values()
            if s.user_id == user_id and s.next_review_at <= now
        ]
        rows.sort(key=lambda s: s.next_review_at)
        return rows


class FakeLearnerPreferenceRepository(AbstractLearnerPreferenceRepository):
    def __init__(self) -> None:
        self.store: dict[tuple[UUID, str], LearnerPreference] = {}

    async def get_or_create(self, user_id: UUID, dimension: str) -> LearnerPreference:
        key = (user_id, dimension)
        if key not in self.store:
            self.store[key] = LearnerPreference(user_id=user_id, dimension=dimension)
        return self.store[key]

    async def update(self, preference: LearnerPreference) -> LearnerPreference:
        self.store[(preference.user_id, preference.dimension)] = preference
        return preference

    async def list_by_user(self, user_id: UUID) -> list[LearnerPreference]:
        rows = [p for p in self.store.values() if p.user_id == user_id]
        rows.sort(key=lambda p: p.confidence, reverse=True)
        return rows


class FakeMasteryRepository(AbstractMasteryRepository):
    def __init__(self) -> None:
        self.store: dict[tuple[UUID, UUID], MasteryRecord] = {}

    async def get_or_create(
        self, user_id: UUID, concept_id: UUID, concept_name: str
    ) -> MasteryRecord:
        key = (user_id, concept_id)
        if key not in self.store:
            self.store[key] = MasteryRecord(
                user_id=user_id, concept_id=concept_id, concept_name=concept_name
            )
        return self.store[key]

    async def update(self, record: MasteryRecord) -> MasteryRecord:
        self.store[(record.user_id, record.concept_id)] = record
        return record

    async def list_by_user(self, user_id: UUID) -> list[MasteryRecord]:
        rows = [r for r in self.store.values() if r.user_id == user_id]
        rows.sort(key=lambda r: r.score, reverse=True)
        return rows

    async def get_by_concept(self, user_id: UUID, concept_id: UUID) -> MasteryRecord | None:
        return self.store.get((user_id, concept_id))

    async def average_score(self, user_id: UUID) -> float:
        rows = [r.score for r in self.store.values() if r.user_id == user_id]
        return round(sum(rows) / len(rows), 2) if rows else 0.0


class FakeConceptNodeRepository(AbstractConceptNodeRepository):
    def __init__(self) -> None:
        self.by_id: dict[UUID, ConceptNode] = {}
        self.by_name: dict[str, ConceptNode] = {}

    async def get_or_create(
        self, name: str, subject: str | None, grade: str | None, chapter: str | None
    ) -> ConceptNode:
        if name in self.by_name:
            return self.by_name[name]
        node = ConceptNode(name=name, subject=subject, grade=grade, chapter=chapter)
        self.by_id[node.id] = node
        self.by_name[name] = node
        return node

    async def get_by_id(self, concept_id: UUID) -> ConceptNode | None:
        return self.by_id.get(concept_id)

    async def get_by_name(
        self, name: str, subject: str | None = None, grade: str | None = None
    ) -> ConceptNode | None:
        return self.by_name.get(name)

    async def list_by_subject_grade(self, subject: str, grade: str) -> list[ConceptNode]:
        return [n for n in self.by_id.values() if n.subject == subject and n.grade == grade]

    async def update(self, node: ConceptNode) -> ConceptNode:
        self.by_id[node.id] = node
        self.by_name[node.name] = node
        return node

    def seed(self, name: str, bloom: str = "Understand", difficulty: str = "medium") -> ConceptNode:
        node = ConceptNode(id=uuid4(), name=name, bloom_level=bloom, difficulty=difficulty)
        self.by_id[node.id] = node
        self.by_name[name] = node
        return node


class FakeLearningGapRepository(AbstractLearningGapRepository):
    def __init__(self) -> None:
        self.store: dict[tuple[UUID, UUID], LearningGap] = {}

    async def get_or_create(
        self, user_id: UUID, concept_id: UUID, concept_name: str, reason: str
    ) -> LearningGap:
        key = (user_id, concept_id)
        if key not in self.store:
            self.store[key] = LearningGap(
                user_id=user_id, concept_id=concept_id, concept_name=concept_name, reason=reason
            )
        return self.store[key]

    async def update(self, gap: LearningGap) -> LearningGap:
        self.store[(gap.user_id, gap.concept_id)] = gap
        return gap

    async def list_by_user(self, user_id: UUID, include_resolved: bool = False) -> list[LearningGap]:
        rows = [g for g in self.store.values() if g.user_id == user_id]
        if not include_resolved:
            rows = [g for g in rows if not g.is_resolved]
        rows.sort(key=lambda g: g.occurrence_count, reverse=True)
        return rows

    async def resolve(self, gap_id: UUID) -> None:
        for g in self.store.values():
            if g.id == gap_id:
                g.resolve()
