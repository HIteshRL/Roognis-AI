from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.learning import (
    BehavioralSignals,
    ConceptEdge,
    ConceptMemory,
    ConceptNode,
    LearningGap,
    LearningSession,
    MasteryRecord,
    StudentProfile,
)
from src.domain.repositories.learning_repository import (
    AbstractConceptEdgeRepository,
    AbstractConceptMemoryRepository,
    AbstractConceptNodeRepository,
    AbstractLearningGapRepository,
    AbstractLearningSessionRepository,
    AbstractMasteryRepository,
    AbstractStudentProfileRepository,
)
from src.infrastructure.database.models.learning import (
    ConceptEdgeModel,
    ConceptMemoryModel,
    ConceptNodeModel,
    LearningGapModel,
    LearningSessionModel,
    MasteryRecordModel,
    StudentProfileModel,
)

# ── Mappers ───────────────────────────────────────────────────────────────────

def _to_profile(m: StudentProfileModel) -> StudentProfile:
    p = StudentProfile.__new__(StudentProfile)
    p.id = UUID(m.id)
    p.user_id = UUID(m.user_id)
    p.institution = m.institution
    p.grade = m.grade
    p.subjects = list(m.subjects or [])
    p.current_chapter = m.current_chapter
    p.learning_velocity = m.learning_velocity
    p.confidence_score = m.confidence_score
    p.behavioral_signals = BehavioralSignals.from_dict(m.behavioral_signals)
    p.last_active = m.last_active
    p.created_at = m.created_at
    p.updated_at = m.updated_at
    return p


def _to_session(m: LearningSessionModel) -> LearningSession:
    s = LearningSession.__new__(LearningSession)
    s.id = UUID(m.id)
    s.user_id = UUID(m.user_id)
    s.conversation_id = UUID(m.conversation_id) if m.conversation_id else None
    s.subject = m.subject
    s.chapter = m.chapter
    s.grade = m.grade
    s.question = m.question
    s.ai_response = m.ai_response
    s.retrieved_context = m.retrieved_context
    s.primary_concept = m.primary_concept
    s.concepts_discussed = list(m.concepts_discussed or [])
    s.skills = list(m.skills or [])
    s.bloom_level = m.bloom_level
    s.difficulty_level = m.difficulty_level
    s.misconceptions = list(m.misconceptions or [])
    s.intent = getattr(m, "intent", "unknown")
    s.token_count = m.token_count
    s.duration_ms = m.duration_ms
    s.created_at = m.created_at
    return s


def _to_node(m: ConceptNodeModel) -> ConceptNode:
    n = ConceptNode.__new__(ConceptNode)
    n.id = UUID(m.id)
    n.name = m.name
    n.subject = m.subject
    n.grade = m.grade
    n.chapter = m.chapter
    n.description = m.description
    n.bloom_level = m.bloom_level
    n.difficulty = m.difficulty
    n.created_at = m.created_at
    n.updated_at = m.updated_at
    return n


def _to_edge(m: ConceptEdgeModel) -> ConceptEdge:
    e = ConceptEdge.__new__(ConceptEdge)
    e.id = UUID(m.id)
    e.source_id = UUID(m.source_id)
    e.target_id = UUID(m.target_id)
    e.weight = m.weight
    e.created_at = m.created_at
    return e


def _to_mastery(m: MasteryRecordModel) -> MasteryRecord:
    r = MasteryRecord.__new__(MasteryRecord)
    r.id = UUID(m.id)
    r.user_id = UUID(m.user_id)
    r.concept_id = UUID(m.concept_id)
    r.concept_name = m.concept_name
    r.score = m.score
    r.interaction_count = m.interaction_count
    r.last_updated = m.last_updated
    r.created_at = m.created_at
    return r


def _to_gap(m: LearningGapModel) -> LearningGap:
    g = LearningGap.__new__(LearningGap)
    g.id = UUID(m.id)
    g.user_id = UUID(m.user_id)
    g.concept_id = UUID(m.concept_id)
    g.concept_name = m.concept_name
    g.severity = m.severity
    g.reason = m.reason
    g.confidence = m.confidence
    g.occurrence_count = m.occurrence_count
    g.is_resolved = m.is_resolved
    g.created_at = m.created_at
    g.updated_at = m.updated_at
    return g


# ── Student Profile ───────────────────────────────────────────────────────────

class StudentProfileRepository(AbstractStudentProfileRepository):
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(self, profile: StudentProfile) -> StudentProfile:
        m = StudentProfileModel(
            id=str(profile.id),
            user_id=str(profile.user_id),
            institution=profile.institution,
            grade=profile.grade,
            subjects=profile.subjects,
            current_chapter=profile.current_chapter,
            learning_velocity=profile.learning_velocity,
            confidence_score=profile.confidence_score,
            behavioral_signals=profile.behavioral_signals.to_dict(),
        )
        self._db.add(m)
        await self._db.flush()
        await self._db.refresh(m)
        return _to_profile(m)

    async def get_by_user_id(self, user_id: UUID) -> StudentProfile | None:
        result = await self._db.execute(
            select(StudentProfileModel).where(StudentProfileModel.user_id == str(user_id))
        )
        m = result.scalar_one_or_none()
        return _to_profile(m) if m else None

    async def update(self, profile: StudentProfile) -> StudentProfile:
        result = await self._db.execute(
            select(StudentProfileModel).where(StudentProfileModel.user_id == str(profile.user_id))
        )
        m = result.scalar_one()
        m.institution = profile.institution
        m.grade = profile.grade
        m.subjects = profile.subjects
        m.current_chapter = profile.current_chapter
        m.learning_velocity = profile.learning_velocity
        m.confidence_score = profile.confidence_score
        m.behavioral_signals = profile.behavioral_signals.to_dict()
        m.last_active = profile.last_active
        m.updated_at = profile.updated_at
        await self._db.flush()
        await self._db.refresh(m)
        return _to_profile(m)

    async def delete(self, user_id: UUID) -> None:
        result = await self._db.execute(
            select(StudentProfileModel).where(StudentProfileModel.user_id == str(user_id))
        )
        m = result.scalar_one_or_none()
        if m:
            await self._db.delete(m)
            await self._db.flush()


# ── Learning Session ──────────────────────────────────────────────────────────

class LearningSessionRepository(AbstractLearningSessionRepository):
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(self, session: LearningSession) -> LearningSession:
        m = LearningSessionModel(
            id=str(session.id),
            user_id=str(session.user_id),
            conversation_id=str(session.conversation_id) if session.conversation_id else None,
            subject=session.subject,
            chapter=session.chapter,
            grade=session.grade,
            question=session.question,
            ai_response=session.ai_response,
            retrieved_context=session.retrieved_context,
            primary_concept=session.primary_concept,
            concepts_discussed=session.concepts_discussed,
            skills=session.skills,
            bloom_level=session.bloom_level,
            difficulty_level=session.difficulty_level,
            misconceptions=session.misconceptions,
            intent=session.intent,
            token_count=session.token_count,
            duration_ms=session.duration_ms,
        )
        self._db.add(m)
        await self._db.flush()
        await self._db.refresh(m)
        return _to_session(m)

    async def list_by_user(self, user_id: UUID, limit: int, offset: int) -> list[LearningSession]:
        result = await self._db.execute(
            select(LearningSessionModel)
            .where(LearningSessionModel.user_id == str(user_id))
            .order_by(LearningSessionModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return [_to_session(m) for m in result.scalars().all()]

    async def count_by_user(self, user_id: UUID) -> int:
        result = await self._db.execute(
            select(func.count(LearningSessionModel.id))
            .where(LearningSessionModel.user_id == str(user_id))
        )
        return result.scalar_one()

    async def recent_concepts(self, user_id: UUID, days: int = 7) -> list[str]:
        cutoff = datetime.now(UTC) - timedelta(days=days)
        result = await self._db.execute(
            select(LearningSessionModel.primary_concept)
            .where(
                LearningSessionModel.user_id == str(user_id),
                LearningSessionModel.created_at >= cutoff,
                LearningSessionModel.primary_concept.isnot(None),
            )
            .order_by(LearningSessionModel.created_at.desc())
            .limit(50)
        )
        return [r for r in result.scalars().all() if r]

    async def list_since(self, user_id: UUID, since: datetime) -> list[LearningSession]:
        result = await self._db.execute(
            select(LearningSessionModel)
            .where(
                LearningSessionModel.user_id == str(user_id),
                LearningSessionModel.created_at >= since,
            )
            .order_by(LearningSessionModel.created_at.desc())
        )
        return [_to_session(m) for m in result.scalars().all()]


# ── Concept Node ──────────────────────────────────────────────────────────────

class ConceptNodeRepository(AbstractConceptNodeRepository):
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_or_create(
        self, name: str, subject: str | None, grade: str | None, chapter: str | None
    ) -> ConceptNode:
        stmt = select(ConceptNodeModel).where(ConceptNodeModel.name == name)
        if subject:
            stmt = stmt.where(ConceptNodeModel.subject == subject)
        if grade:
            stmt = stmt.where(ConceptNodeModel.grade == grade)
        result = await self._db.execute(stmt)
        m = result.scalar_one_or_none()
        if m:
            return _to_node(m)

        from uuid import uuid4
        m = ConceptNodeModel(
            id=str(uuid4()),
            name=name,
            subject=subject,
            grade=grade,
            chapter=chapter,
        )
        self._db.add(m)
        await self._db.flush()
        await self._db.refresh(m)
        return _to_node(m)

    async def get_by_id(self, concept_id: UUID) -> ConceptNode | None:
        result = await self._db.execute(
            select(ConceptNodeModel).where(ConceptNodeModel.id == str(concept_id))
        )
        m = result.scalar_one_or_none()
        return _to_node(m) if m else None

    async def get_by_name(
        self, name: str, subject: str | None = None, grade: str | None = None
    ) -> ConceptNode | None:
        stmt = select(ConceptNodeModel).where(ConceptNodeModel.name == name)
        if subject:
            stmt = stmt.where(ConceptNodeModel.subject == subject)
        if grade:
            stmt = stmt.where(ConceptNodeModel.grade == grade)
        result = await self._db.execute(stmt)
        m = result.scalar_one_or_none()
        return _to_node(m) if m else None

    async def list_by_subject_grade(self, subject: str, grade: str) -> list[ConceptNode]:
        result = await self._db.execute(
            select(ConceptNodeModel)
            .where(
                ConceptNodeModel.subject == subject,
                ConceptNodeModel.grade == grade,
            )
            .order_by(ConceptNodeModel.name)
        )
        return [_to_node(m) for m in result.scalars().all()]

    async def update(self, node: ConceptNode) -> ConceptNode:
        result = await self._db.execute(
            select(ConceptNodeModel).where(ConceptNodeModel.id == str(node.id))
        )
        m = result.scalar_one()
        m.description = node.description
        m.bloom_level = node.bloom_level
        m.difficulty = node.difficulty
        m.updated_at = node.updated_at
        await self._db.flush()
        await self._db.refresh(m)
        return _to_node(m)


# ── Concept Edge ──────────────────────────────────────────────────────────────

class ConceptEdgeRepository(AbstractConceptEdgeRepository):
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(self, edge: ConceptEdge) -> ConceptEdge:
        m = ConceptEdgeModel(
            id=str(edge.id),
            source_id=str(edge.source_id),
            target_id=str(edge.target_id),
            weight=edge.weight,
        )
        self._db.add(m)
        await self._db.flush()
        await self._db.refresh(m)
        return _to_edge(m)

    async def get_prerequisites(self, concept_id: UUID) -> list[ConceptNode]:
        result = await self._db.execute(
            select(ConceptNodeModel)
            .join(ConceptEdgeModel, ConceptEdgeModel.source_id == ConceptNodeModel.id)
            .where(ConceptEdgeModel.target_id == str(concept_id))
        )
        return [_to_node(m) for m in result.scalars().all()]

    async def get_successors(self, concept_id: UUID) -> list[ConceptNode]:
        result = await self._db.execute(
            select(ConceptNodeModel)
            .join(ConceptEdgeModel, ConceptEdgeModel.target_id == ConceptNodeModel.id)
            .where(ConceptEdgeModel.source_id == str(concept_id))
        )
        return [_to_node(m) for m in result.scalars().all()]

    async def exists(self, source_id: UUID, target_id: UUID) -> bool:
        result = await self._db.execute(
            select(func.count(ConceptEdgeModel.id)).where(
                ConceptEdgeModel.source_id == str(source_id),
                ConceptEdgeModel.target_id == str(target_id),
            )
        )
        return result.scalar_one() > 0


# ── Mastery Record ────────────────────────────────────────────────────────────

class MasteryRepository(AbstractMasteryRepository):
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_or_create(
        self, user_id: UUID, concept_id: UUID, concept_name: str
    ) -> MasteryRecord:
        result = await self._db.execute(
            select(MasteryRecordModel).where(
                MasteryRecordModel.user_id == str(user_id),
                MasteryRecordModel.concept_id == str(concept_id),
            )
        )
        m = result.scalar_one_or_none()
        if m:
            return _to_mastery(m)

        from uuid import uuid4
        m = MasteryRecordModel(
            id=str(uuid4()),
            user_id=str(user_id),
            concept_id=str(concept_id),
            concept_name=concept_name,
        )
        self._db.add(m)
        await self._db.flush()
        await self._db.refresh(m)
        return _to_mastery(m)

    async def update(self, record: MasteryRecord) -> MasteryRecord:
        result = await self._db.execute(
            select(MasteryRecordModel).where(MasteryRecordModel.id == str(record.id))
        )
        m = result.scalar_one()
        m.score = record.score
        m.interaction_count = record.interaction_count
        m.last_updated = record.last_updated
        await self._db.flush()
        await self._db.refresh(m)
        return _to_mastery(m)

    async def list_by_user(self, user_id: UUID) -> list[MasteryRecord]:
        result = await self._db.execute(
            select(MasteryRecordModel)
            .where(MasteryRecordModel.user_id == str(user_id))
            .order_by(MasteryRecordModel.score.desc())
        )
        return [_to_mastery(m) for m in result.scalars().all()]

    async def get_by_concept(self, user_id: UUID, concept_id: UUID) -> MasteryRecord | None:
        result = await self._db.execute(
            select(MasteryRecordModel).where(
                MasteryRecordModel.user_id == str(user_id),
                MasteryRecordModel.concept_id == str(concept_id),
            )
        )
        m = result.scalar_one_or_none()
        return _to_mastery(m) if m else None

    async def average_score(self, user_id: UUID) -> float:
        result = await self._db.execute(
            select(func.avg(MasteryRecordModel.score)).where(
                MasteryRecordModel.user_id == str(user_id)
            )
        )
        val = result.scalar_one()
        return round(float(val), 2) if val else 0.0


# ── Learning Gap ──────────────────────────────────────────────────────────────

class LearningGapRepository(AbstractLearningGapRepository):
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_or_create(
        self, user_id: UUID, concept_id: UUID, concept_name: str, reason: str
    ) -> LearningGap:
        result = await self._db.execute(
            select(LearningGapModel).where(
                LearningGapModel.user_id == str(user_id),
                LearningGapModel.concept_id == str(concept_id),
            )
        )
        m = result.scalar_one_or_none()
        if m:
            return _to_gap(m)

        from uuid import uuid4
        m = LearningGapModel(
            id=str(uuid4()),
            user_id=str(user_id),
            concept_id=str(concept_id),
            concept_name=concept_name,
            reason=reason,
        )
        self._db.add(m)
        await self._db.flush()
        await self._db.refresh(m)
        return _to_gap(m)

    async def update(self, gap: LearningGap) -> LearningGap:
        result = await self._db.execute(
            select(LearningGapModel).where(LearningGapModel.id == str(gap.id))
        )
        m = result.scalar_one()
        m.severity = gap.severity
        m.reason = gap.reason
        m.confidence = gap.confidence
        m.occurrence_count = gap.occurrence_count
        m.is_resolved = gap.is_resolved
        m.updated_at = gap.updated_at
        await self._db.flush()
        await self._db.refresh(m)
        return _to_gap(m)

    async def list_by_user(
        self, user_id: UUID, include_resolved: bool = False
    ) -> list[LearningGap]:
        stmt = select(LearningGapModel).where(LearningGapModel.user_id == str(user_id))
        if not include_resolved:
            stmt = stmt.where(LearningGapModel.is_resolved.is_(False))
        stmt = stmt.order_by(LearningGapModel.occurrence_count.desc())
        result = await self._db.execute(stmt)
        return [_to_gap(m) for m in result.scalars().all()]

    async def resolve(self, gap_id: UUID) -> None:
        result = await self._db.execute(
            select(LearningGapModel).where(LearningGapModel.id == str(gap_id))
        )
        m = result.scalar_one_or_none()
        if m:
            m.is_resolved = True
            m.updated_at = datetime.now(UTC)
            await self._db.flush()


# ── Concept Memory ────────────────────────────────────────────────────────────

def _to_memory(m: ConceptMemoryModel) -> ConceptMemory:
    c = ConceptMemory.__new__(ConceptMemory)
    c.id = UUID(m.id)
    c.user_id = UUID(m.user_id)
    c.concept_id = UUID(m.concept_id)
    c.concept_name = m.concept_name
    c.times_taught = m.times_taught
    c.successful_approaches = m.successful_approaches
    c.failed_approaches = m.failed_approaches
    c.last_approach = m.last_approach
    c.teaching_notes = list(m.teaching_notes or [])
    c.last_taught = m.last_taught
    c.created_at = m.created_at
    c.updated_at = m.updated_at
    return c


class ConceptMemoryRepository(AbstractConceptMemoryRepository):
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_or_create(
        self, user_id: UUID, concept_id: UUID, concept_name: str
    ) -> ConceptMemory:
        result = await self._db.execute(
            select(ConceptMemoryModel).where(
                ConceptMemoryModel.user_id == str(user_id),
                ConceptMemoryModel.concept_id == str(concept_id),
            )
        )
        m = result.scalar_one_or_none()
        if m:
            return _to_memory(m)

        from uuid import uuid4
        m = ConceptMemoryModel(
            id=str(uuid4()),
            user_id=str(user_id),
            concept_id=str(concept_id),
            concept_name=concept_name,
        )
        self._db.add(m)
        await self._db.flush()
        await self._db.refresh(m)
        return _to_memory(m)

    async def update(self, memory: ConceptMemory) -> ConceptMemory:
        result = await self._db.execute(
            select(ConceptMemoryModel).where(ConceptMemoryModel.id == str(memory.id))
        )
        m = result.scalar_one()
        m.times_taught = memory.times_taught
        m.successful_approaches = memory.successful_approaches
        m.failed_approaches = memory.failed_approaches
        m.last_approach = memory.last_approach
        m.teaching_notes = memory.teaching_notes
        m.last_taught = memory.last_taught
        m.updated_at = memory.updated_at
        await self._db.flush()
        await self._db.refresh(m)
        return _to_memory(m)

    async def list_by_user(self, user_id: UUID) -> list[ConceptMemory]:
        result = await self._db.execute(
            select(ConceptMemoryModel)
            .where(ConceptMemoryModel.user_id == str(user_id))
            .order_by(ConceptMemoryModel.times_taught.desc())
        )
        return [_to_memory(m) for m in result.scalars().all()]

    async def get_by_concept(self, user_id: UUID, concept_id: UUID) -> ConceptMemory | None:
        result = await self._db.execute(
            select(ConceptMemoryModel).where(
                ConceptMemoryModel.user_id == str(user_id),
                ConceptMemoryModel.concept_id == str(concept_id),
            )
        )
        m = result.scalar_one_or_none()
        return _to_memory(m) if m else None
