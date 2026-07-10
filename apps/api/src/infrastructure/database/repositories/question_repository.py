"""Concrete SQLAlchemy repositories for the questioning + evidence subsystem."""
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.question import (
    GeneratedQuestion,
    LearnerEvidence,
    LearnerPreference,
    RecallSchedule,
)
from src.domain.repositories.question_repository import (
    AbstractEvidenceRepository,
    AbstractLearnerPreferenceRepository,
    AbstractLearnerQuestionRepository,
    AbstractRecallScheduleRepository,
)
from src.infrastructure.database.models.question import (
    LearnerEvidenceModel,
    LearnerPreferenceModel,
    LearnerQuestionModel,
    RecallScheduleModel,
)

# ── Mappers ───────────────────────────────────────────────────────────────────

def _to_evidence(m: LearnerEvidenceModel) -> LearnerEvidence:
    e = LearnerEvidence.__new__(LearnerEvidence)
    e.id = UUID(m.id)
    e.user_id = UUID(m.user_id)
    e.concept_id = UUID(m.concept_id) if m.concept_id else None
    e.concept_name = m.concept_name
    e.signal = m.signal
    e.objective = m.objective
    e.source = m.source
    e.weight = m.weight
    e.bloom_level = m.bloom_level
    e.intent = m.intent
    e.question_id = UUID(m.question_id) if m.question_id else None
    e.confidence_before = m.confidence_before
    e.confidence_after = m.confidence_after
    e.detail = m.detail
    e.created_at = m.created_at
    return e


def _to_question(m: LearnerQuestionModel) -> GeneratedQuestion:
    q = GeneratedQuestion.__new__(GeneratedQuestion)
    q.id = UUID(m.id)
    q.user_id = UUID(m.user_id)
    q.concept_id = UUID(m.concept_id)
    q.concept_name = m.concept_name
    q.question_text = m.question_text
    q.objective = m.objective
    q.purpose = m.purpose
    q.difficulty = m.difficulty
    q.bloom_level = m.bloom_level
    q.expected_answer = m.expected_answer
    q.confidence_threshold = m.confidence_threshold
    q.evidence_weight = m.evidence_weight
    q.status = m.status
    q.student_answer = m.student_answer
    q.is_correct = m.is_correct
    q.score = m.score
    q.feedback = m.feedback
    q.scheduled_for = m.scheduled_for
    q.asked_at = m.asked_at
    q.answered_at = m.answered_at
    q.created_at = m.created_at
    q.updated_at = m.updated_at
    return q


def _to_schedule(m: RecallScheduleModel) -> RecallSchedule:
    s = RecallSchedule.__new__(RecallSchedule)
    s.id = UUID(m.id)
    s.user_id = UUID(m.user_id)
    s.concept_id = UUID(m.concept_id)
    s.concept_name = m.concept_name
    s.interval_days = m.interval_days
    s.ease_factor = m.ease_factor
    s.repetitions = m.repetitions
    s.lapses = m.lapses
    s.retention_probability = m.retention_probability
    s.last_reviewed = m.last_reviewed
    s.next_review_at = m.next_review_at
    s.created_at = m.created_at
    s.updated_at = m.updated_at
    return s


def _to_preference(m: LearnerPreferenceModel) -> LearnerPreference:
    p = LearnerPreference.__new__(LearnerPreference)
    p.id = UUID(m.id)
    p.user_id = UUID(m.user_id)
    p.dimension = m.dimension
    p.strength = m.strength
    p.confidence = m.confidence
    p.evidence_count = m.evidence_count
    p.last_updated = m.last_updated
    p.created_at = m.created_at
    return p


# ── Evidence (append-only) ──────────────────────────────────────────────────────

class EvidenceRepository(AbstractEvidenceRepository):
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def add(self, evidence: LearnerEvidence) -> LearnerEvidence:
        m = LearnerEvidenceModel(
            id=str(evidence.id),
            user_id=str(evidence.user_id),
            concept_id=str(evidence.concept_id) if evidence.concept_id else None,
            concept_name=evidence.concept_name,
            signal=evidence.signal,
            objective=evidence.objective,
            source=evidence.source,
            weight=evidence.weight,
            bloom_level=evidence.bloom_level,
            intent=evidence.intent,
            question_id=str(evidence.question_id) if evidence.question_id else None,
            confidence_before=evidence.confidence_before,
            confidence_after=evidence.confidence_after,
            detail=evidence.detail,
        )
        self._db.add(m)
        await self._db.flush()
        await self._db.refresh(m)
        return _to_evidence(m)

    async def list_by_user(self, user_id: UUID, limit: int = 100) -> list[LearnerEvidence]:
        result = await self._db.execute(
            select(LearnerEvidenceModel)
            .where(LearnerEvidenceModel.user_id == str(user_id))
            .order_by(LearnerEvidenceModel.created_at.desc())
            .limit(limit)
        )
        return [_to_evidence(m) for m in result.scalars().all()]

    async def list_by_concept(
        self, user_id: UUID, concept_id: UUID, limit: int = 50
    ) -> list[LearnerEvidence]:
        result = await self._db.execute(
            select(LearnerEvidenceModel)
            .where(
                LearnerEvidenceModel.user_id == str(user_id),
                LearnerEvidenceModel.concept_id == str(concept_id),
            )
            .order_by(LearnerEvidenceModel.created_at.desc())
            .limit(limit)
        )
        return [_to_evidence(m) for m in result.scalars().all()]

    async def count_by_concept(self, user_id: UUID, concept_id: UUID) -> int:
        result = await self._db.execute(
            select(func.count(LearnerEvidenceModel.id)).where(
                LearnerEvidenceModel.user_id == str(user_id),
                LearnerEvidenceModel.concept_id == str(concept_id),
            )
        )
        return result.scalar_one()


# ── Generated questions ──────────────────────────────────────────────────────────

class LearnerQuestionRepository(AbstractLearnerQuestionRepository):
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(self, question: GeneratedQuestion) -> GeneratedQuestion:
        m = LearnerQuestionModel(
            id=str(question.id),
            user_id=str(question.user_id),
            concept_id=str(question.concept_id),
            concept_name=question.concept_name,
            question_text=question.question_text,
            objective=question.objective,
            purpose=question.purpose,
            difficulty=question.difficulty,
            bloom_level=question.bloom_level,
            expected_answer=question.expected_answer,
            confidence_threshold=question.confidence_threshold,
            evidence_weight=question.evidence_weight,
            status=question.status,
            student_answer=question.student_answer,
            is_correct=question.is_correct,
            score=question.score,
            feedback=question.feedback,
            scheduled_for=question.scheduled_for,
            asked_at=question.asked_at,
            answered_at=question.answered_at,
        )
        self._db.add(m)
        await self._db.flush()
        await self._db.refresh(m)
        return _to_question(m)

    async def update(self, question: GeneratedQuestion) -> GeneratedQuestion:
        result = await self._db.execute(
            select(LearnerQuestionModel).where(LearnerQuestionModel.id == str(question.id))
        )
        m = result.scalar_one()
        m.status = question.status
        m.student_answer = question.student_answer
        m.is_correct = question.is_correct
        m.score = question.score
        m.feedback = question.feedback
        m.asked_at = question.asked_at
        m.answered_at = question.answered_at
        m.updated_at = question.updated_at
        await self._db.flush()
        await self._db.refresh(m)
        return _to_question(m)

    async def get_by_id(self, question_id: UUID) -> GeneratedQuestion | None:
        result = await self._db.execute(
            select(LearnerQuestionModel).where(LearnerQuestionModel.id == str(question_id))
        )
        m = result.scalar_one_or_none()
        return _to_question(m) if m else None

    async def list_by_user(
        self, user_id: UUID, status: str | None = None, limit: int = 20
    ) -> list[GeneratedQuestion]:
        stmt = select(LearnerQuestionModel).where(LearnerQuestionModel.user_id == str(user_id))
        if status:
            stmt = stmt.where(LearnerQuestionModel.status == status)
        stmt = stmt.order_by(LearnerQuestionModel.created_at.desc()).limit(limit)
        result = await self._db.execute(stmt)
        return [_to_question(m) for m in result.scalars().all()]

    async def next_pending(self, user_id: UUID) -> GeneratedQuestion | None:
        result = await self._db.execute(
            select(LearnerQuestionModel)
            .where(
                LearnerQuestionModel.user_id == str(user_id),
                LearnerQuestionModel.status.in_(["pending", "asked"]),
            )
            .order_by(LearnerQuestionModel.created_at.asc())
            .limit(1)
        )
        m = result.scalar_one_or_none()
        return _to_question(m) if m else None


# ── Recall schedules ─────────────────────────────────────────────────────────────

class RecallScheduleRepository(AbstractRecallScheduleRepository):
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_or_create(
        self, user_id: UUID, concept_id: UUID, concept_name: str
    ) -> RecallSchedule:
        result = await self._db.execute(
            select(RecallScheduleModel).where(
                RecallScheduleModel.user_id == str(user_id),
                RecallScheduleModel.concept_id == str(concept_id),
            )
        )
        m = result.scalar_one_or_none()
        if m:
            return _to_schedule(m)

        m = RecallScheduleModel(
            id=str(uuid4()),
            user_id=str(user_id),
            concept_id=str(concept_id),
            concept_name=concept_name,
        )
        self._db.add(m)
        await self._db.flush()
        await self._db.refresh(m)
        return _to_schedule(m)

    async def update(self, schedule: RecallSchedule) -> RecallSchedule:
        result = await self._db.execute(
            select(RecallScheduleModel).where(RecallScheduleModel.id == str(schedule.id))
        )
        m = result.scalar_one()
        m.interval_days = schedule.interval_days
        m.ease_factor = schedule.ease_factor
        m.repetitions = schedule.repetitions
        m.lapses = schedule.lapses
        m.retention_probability = schedule.retention_probability
        m.last_reviewed = schedule.last_reviewed
        m.next_review_at = schedule.next_review_at
        m.updated_at = schedule.updated_at
        await self._db.flush()
        await self._db.refresh(m)
        return _to_schedule(m)

    async def get_by_concept(self, user_id: UUID, concept_id: UUID) -> RecallSchedule | None:
        result = await self._db.execute(
            select(RecallScheduleModel).where(
                RecallScheduleModel.user_id == str(user_id),
                RecallScheduleModel.concept_id == str(concept_id),
            )
        )
        m = result.scalar_one_or_none()
        return _to_schedule(m) if m else None

    async def list_by_user(self, user_id: UUID) -> list[RecallSchedule]:
        result = await self._db.execute(
            select(RecallScheduleModel)
            .where(RecallScheduleModel.user_id == str(user_id))
            .order_by(RecallScheduleModel.next_review_at.asc())
        )
        return [_to_schedule(m) for m in result.scalars().all()]

    async def list_due(self, user_id: UUID, now: datetime) -> list[RecallSchedule]:
        result = await self._db.execute(
            select(RecallScheduleModel)
            .where(
                RecallScheduleModel.user_id == str(user_id),
                RecallScheduleModel.next_review_at <= now,
            )
            .order_by(RecallScheduleModel.next_review_at.asc())
        )
        return [_to_schedule(m) for m in result.scalars().all()]


# ── Learner preferences ──────────────────────────────────────────────────────────

class LearnerPreferenceRepository(AbstractLearnerPreferenceRepository):
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_or_create(self, user_id: UUID, dimension: str) -> LearnerPreference:
        result = await self._db.execute(
            select(LearnerPreferenceModel).where(
                LearnerPreferenceModel.user_id == str(user_id),
                LearnerPreferenceModel.dimension == dimension,
            )
        )
        m = result.scalar_one_or_none()
        if m:
            return _to_preference(m)

        m = LearnerPreferenceModel(
            id=str(uuid4()),
            user_id=str(user_id),
            dimension=dimension,
        )
        self._db.add(m)
        await self._db.flush()
        await self._db.refresh(m)
        return _to_preference(m)

    async def update(self, preference: LearnerPreference) -> LearnerPreference:
        result = await self._db.execute(
            select(LearnerPreferenceModel).where(LearnerPreferenceModel.id == str(preference.id))
        )
        m = result.scalar_one()
        m.strength = preference.strength
        m.confidence = preference.confidence
        m.evidence_count = preference.evidence_count
        m.last_updated = preference.last_updated
        await self._db.flush()
        await self._db.refresh(m)
        return _to_preference(m)

    async def list_by_user(self, user_id: UUID) -> list[LearnerPreference]:
        result = await self._db.execute(
            select(LearnerPreferenceModel)
            .where(LearnerPreferenceModel.user_id == str(user_id))
            .order_by(LearnerPreferenceModel.confidence.desc())
        )
        return [_to_preference(m) for m in result.scalars().all()]
