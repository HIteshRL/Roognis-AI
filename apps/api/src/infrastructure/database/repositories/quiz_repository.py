from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.quiz import (
    BankedQuestion,
    Quiz,
    QuizAttempt,
    QuizQuestion,
    QuizResponse,
)
from src.domain.repositories.quiz_repository import (
    AbstractQuestionBankRepository,
    AbstractQuizAttemptRepository,
    AbstractQuizQuestionRepository,
    AbstractQuizRepository,
    AbstractQuizResponseRepository,
)
from src.infrastructure.database.models.quiz import (
    QuestionBankModel,
    QuizAttemptModel,
    QuizModel,
    QuizQuestionModel,
    QuizResponseModel,
)

# ── Mappers ──────────────────────────────────────────────────────────────────


def _to_quiz(m: QuizModel) -> Quiz:
    q = Quiz.__new__(Quiz)
    q.id = UUID(m.id)
    q.user_id = UUID(m.user_id)
    q.title = m.title
    q.subject = m.subject
    q.chapter = m.chapter
    q.difficulty = m.difficulty
    q.question_count = m.question_count
    q.total_attempts = m.total_attempts
    q.best_score = m.best_score
    q.created_at = m.created_at
    q.updated_at = m.updated_at
    return q


def _to_question(m: QuizQuestionModel) -> QuizQuestion:
    q = QuizQuestion.__new__(QuizQuestion)
    q.id = UUID(m.id)
    q.quiz_id = UUID(m.quiz_id)
    q.concept_name = m.concept_name
    q.concept_id = UUID(m.concept_id) if m.concept_id else None
    q.question_text = m.question_text
    q.question_type = m.question_type
    q.options = list(m.options or [])
    q.correct_answer = m.correct_answer
    q.explanation = m.explanation
    q.bloom_level = m.bloom_level
    q.difficulty = m.difficulty
    q.position = m.position
    q.bank_question_id = UUID(m.bank_question_id) if m.bank_question_id else None
    q.created_at = m.created_at
    return q


def _to_banked(m: QuestionBankModel) -> BankedQuestion:
    b = BankedQuestion.__new__(BankedQuestion)
    b.id = UUID(m.id)
    b.concept_id = UUID(m.concept_id) if m.concept_id else None
    b.concept_name = m.concept_name
    b.question_text = m.question_text
    b.question_type = m.question_type
    b.options = list(m.options or [])
    b.correct_answer = m.correct_answer
    b.explanation = m.explanation
    b.bloom_level = m.bloom_level
    b.difficulty = m.difficulty
    b.difficulty_rating = m.difficulty_rating
    b.times_served = m.times_served
    b.times_correct = m.times_correct
    b.version = m.version
    b.source = m.source
    b.is_active = m.is_active
    b.created_at = m.created_at
    b.updated_at = m.updated_at
    return b


def _to_attempt(m: QuizAttemptModel) -> QuizAttempt:
    a = QuizAttempt.__new__(QuizAttempt)
    a.id = UUID(m.id)
    a.user_id = UUID(m.user_id)
    a.quiz_id = UUID(m.quiz_id)
    a.started_at = m.started_at
    a.completed_at = m.completed_at
    a.score = m.score
    a.correct_count = m.correct_count
    a.total_answered = m.total_answered
    a.total_time_ms = m.total_time_ms
    a.created_at = m.created_at
    return a


def _to_response(m: QuizResponseModel) -> QuizResponse:
    r = QuizResponse.__new__(QuizResponse)
    r.id = UUID(m.id)
    r.attempt_id = UUID(m.attempt_id)
    r.question_id = UUID(m.question_id)
    r.selected_answer = m.selected_answer
    r.is_correct = m.is_correct
    r.time_spent_ms = m.time_spent_ms
    r.created_at = m.created_at
    return r


# ── Repositories ─────────────────────────────────────────────────────────────


class QuizRepository(AbstractQuizRepository):
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(self, quiz: Quiz) -> Quiz:
        m = QuizModel(
            id=str(quiz.id),
            user_id=str(quiz.user_id),
            title=quiz.title,
            subject=quiz.subject,
            chapter=quiz.chapter,
            difficulty=quiz.difficulty,
            question_count=quiz.question_count,
            total_attempts=quiz.total_attempts,
            best_score=quiz.best_score,
        )
        self._db.add(m)
        await self._db.flush()
        await self._db.refresh(m)
        return _to_quiz(m)

    async def get_by_id(self, quiz_id: UUID) -> Quiz | None:
        result = await self._db.execute(
            select(QuizModel).where(QuizModel.id == str(quiz_id))
        )
        m = result.scalar_one_or_none()
        return _to_quiz(m) if m else None

    async def list_by_user(
        self, user_id: UUID, subject: str | None, limit: int, offset: int
    ) -> list[Quiz]:
        stmt = (
            select(QuizModel)
            .where(QuizModel.user_id == str(user_id))
            .order_by(QuizModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if subject:
            stmt = stmt.where(QuizModel.subject == subject)
        result = await self._db.execute(stmt)
        return [_to_quiz(m) for m in result.scalars().all()]

    async def count_by_user(
        self, user_id: UUID, subject: str | None = None
    ) -> int:
        stmt = select(func.count(QuizModel.id)).where(
            QuizModel.user_id == str(user_id)
        )
        if subject:
            stmt = stmt.where(QuizModel.subject == subject)
        result = await self._db.execute(stmt)
        return result.scalar_one()

    async def update(self, quiz: Quiz) -> Quiz:
        result = await self._db.execute(
            select(QuizModel).where(QuizModel.id == str(quiz.id))
        )
        m = result.scalar_one()
        m.title = quiz.title
        m.subject = quiz.subject
        m.chapter = quiz.chapter
        m.difficulty = quiz.difficulty
        m.question_count = quiz.question_count
        m.total_attempts = quiz.total_attempts
        m.best_score = quiz.best_score
        await self._db.flush()
        await self._db.refresh(m)
        return _to_quiz(m)

    async def delete(self, quiz_id: UUID) -> None:
        result = await self._db.execute(
            select(QuizModel).where(QuizModel.id == str(quiz_id))
        )
        m = result.scalar_one_or_none()
        if m:
            await self._db.delete(m)
            await self._db.flush()


class QuizQuestionRepository(AbstractQuizQuestionRepository):
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create_many(
        self, questions: list[QuizQuestion]
    ) -> list[QuizQuestion]:
        models = []
        for q in questions:
            m = QuizQuestionModel(
                id=str(q.id),
                quiz_id=str(q.quiz_id),
                concept_name=q.concept_name,
                concept_id=str(q.concept_id) if q.concept_id else None,
                question_text=q.question_text,
                question_type=q.question_type,
                options=q.options,
                correct_answer=q.correct_answer,
                explanation=q.explanation,
                bloom_level=q.bloom_level,
                difficulty=q.difficulty,
                position=q.position,
                bank_question_id=str(q.bank_question_id) if q.bank_question_id else None,
            )
            self._db.add(m)
            models.append(m)
        await self._db.flush()
        for m in models:
            await self._db.refresh(m)
        return [_to_question(m) for m in models]

    async def list_by_quiz(self, quiz_id: UUID) -> list[QuizQuestion]:
        result = await self._db.execute(
            select(QuizQuestionModel)
            .where(QuizQuestionModel.quiz_id == str(quiz_id))
            .order_by(QuizQuestionModel.position)
        )
        return [_to_question(m) for m in result.scalars().all()]


class QuizAttemptRepository(AbstractQuizAttemptRepository):
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(self, attempt: QuizAttempt) -> QuizAttempt:
        m = QuizAttemptModel(
            id=str(attempt.id),
            user_id=str(attempt.user_id),
            quiz_id=str(attempt.quiz_id),
        )
        self._db.add(m)
        await self._db.flush()
        await self._db.refresh(m)
        return _to_attempt(m)

    async def get_by_id(self, attempt_id: UUID) -> QuizAttempt | None:
        result = await self._db.execute(
            select(QuizAttemptModel).where(
                QuizAttemptModel.id == str(attempt_id)
            )
        )
        m = result.scalar_one_or_none()
        return _to_attempt(m) if m else None

    async def list_by_user(
        self, user_id: UUID, limit: int, offset: int
    ) -> list[QuizAttempt]:
        result = await self._db.execute(
            select(QuizAttemptModel)
            .where(QuizAttemptModel.user_id == str(user_id))
            .order_by(QuizAttemptModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return [_to_attempt(m) for m in result.scalars().all()]

    async def update(self, attempt: QuizAttempt) -> QuizAttempt:
        result = await self._db.execute(
            select(QuizAttemptModel).where(
                QuizAttemptModel.id == str(attempt.id)
            )
        )
        m = result.scalar_one()
        m.completed_at = attempt.completed_at
        m.score = attempt.score
        m.correct_count = attempt.correct_count
        m.total_answered = attempt.total_answered
        m.total_time_ms = attempt.total_time_ms
        await self._db.flush()
        await self._db.refresh(m)
        return _to_attempt(m)


class QuizResponseRepository(AbstractQuizResponseRepository):
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(self, response: QuizResponse) -> QuizResponse:
        m = QuizResponseModel(
            id=str(response.id),
            attempt_id=str(response.attempt_id),
            question_id=str(response.question_id),
            selected_answer=response.selected_answer,
            is_correct=response.is_correct,
            time_spent_ms=response.time_spent_ms,
        )
        self._db.add(m)
        await self._db.flush()
        await self._db.refresh(m)
        return _to_response(m)

    async def list_by_attempt(self, attempt_id: UUID) -> list[QuizResponse]:
        result = await self._db.execute(
            select(QuizResponseModel).where(
                QuizResponseModel.attempt_id == str(attempt_id)
            )
        )
        return [_to_response(m) for m in result.scalars().all()]


class QuestionBankRepository(AbstractQuestionBankRepository):
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create_many(self, questions: list[BankedQuestion]) -> list[BankedQuestion]:
        models = []
        for q in questions:
            m = QuestionBankModel(
                id=str(q.id),
                concept_id=str(q.concept_id) if q.concept_id else None,
                concept_name=q.concept_name,
                question_text=q.question_text,
                question_type=q.question_type,
                options=q.options,
                correct_answer=q.correct_answer,
                explanation=q.explanation,
                bloom_level=q.bloom_level,
                difficulty=q.difficulty,
                difficulty_rating=q.difficulty_rating,
                version=q.version,
                source=q.source,
                is_active=q.is_active,
            )
            self._db.add(m)
            models.append(m)
        await self._db.flush()
        for m in models:
            await self._db.refresh(m)
        return [_to_banked(m) for m in models]

    async def get_by_id(self, question_id: UUID) -> BankedQuestion | None:
        result = await self._db.execute(
            select(QuestionBankModel).where(QuestionBankModel.id == str(question_id))
        )
        m = result.scalar_one_or_none()
        return _to_banked(m) if m else None

    async def list_for_concept(
        self, concept_id: UUID, near_rating: float | None = None, limit: int = 5
    ) -> list[BankedQuestion]:
        """Active banked questions for a concept. When near_rating is given,
        return the items whose difficulty_rating is closest to it (maximum-
        information selection); otherwise most-recently-added first."""
        stmt = select(QuestionBankModel).where(
            QuestionBankModel.concept_id == str(concept_id),
            QuestionBankModel.is_active.is_(True),
        )
        if near_rating is not None:
            stmt = stmt.order_by(
                func.abs(QuestionBankModel.difficulty_rating - near_rating)
            )
        else:
            stmt = stmt.order_by(QuestionBankModel.created_at.desc())
        stmt = stmt.limit(limit)
        result = await self._db.execute(stmt)
        return [_to_banked(m) for m in result.scalars().all()]

    async def count_for_concept(self, concept_id: UUID) -> int:
        result = await self._db.execute(
            select(func.count(QuestionBankModel.id)).where(
                QuestionBankModel.concept_id == str(concept_id),
                QuestionBankModel.is_active.is_(True),
            )
        )
        return result.scalar_one()

    async def update_stats(self, question: BankedQuestion) -> None:
        result = await self._db.execute(
            select(QuestionBankModel).where(QuestionBankModel.id == str(question.id))
        )
        m = result.scalar_one_or_none()
        if m is None:
            return
        m.difficulty_rating = question.difficulty_rating
        m.times_served = question.times_served
        m.times_correct = question.times_correct
        m.updated_at = question.updated_at
        await self._db.flush()
