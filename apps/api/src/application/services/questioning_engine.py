"""
QuestioningEngine — the QuestionEngine entry point (facade).

Two responsibilities, both aimed solely at reducing learner uncertainty:
  - ``next_question``: pick the highest-uncertainty target, generate an adaptive
    question for it, persist it as asked, and return it. Reuses an outstanding
    question rather than piling up new ones.
  - ``submit_answer``: evaluate the answer, fold the result into learner state
    (mastery + gaps + recall + confidence) via the ConfidenceUpdater, and return
    the evaluation.
"""
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

import structlog

from src.application.services.answer_evaluator import AnswerEvaluator
from src.application.services.confidence_updater import ConfidenceUpdater
from src.application.services.question_generator import QuestionGenerator
from src.application.services.question_scheduler import QuestionScheduler
from src.domain.entities.question import AnswerEvaluation, GeneratedQuestion, LearnerEvidence
from src.domain.repositories.question_repository import AbstractLearnerQuestionRepository

logger = structlog.get_logger(__name__)


class QuestionOwnershipError(Exception):
    """Raised when a question does not belong to the requesting user."""


@dataclass
class SubmissionResult:
    question: GeneratedQuestion
    evaluation: AnswerEvaluation
    evidence: LearnerEvidence | None
    confidence_after: float


class QuestioningEngine:
    def __init__(
        self,
        scheduler: QuestionScheduler,
        generator: QuestionGenerator,
        evaluator: AnswerEvaluator,
        confidence_updater: ConfidenceUpdater,
        question_repo: AbstractLearnerQuestionRepository,
    ) -> None:
        self._scheduler = scheduler
        self._generator = generator
        self._evaluator = evaluator
        self._confidence = confidence_updater
        self._questions = question_repo

    async def next_question(
        self, user_id: UUID, now: datetime | None = None
    ) -> GeneratedQuestion | None:
        now = now or datetime.now(UTC)

        # Don't stack questions — hand back an outstanding one if it exists.
        outstanding = await self._questions.next_pending(user_id)
        if outstanding is not None:
            return outstanding

        target = await self._scheduler.next_target(user_id, now)
        if target is None:
            return None

        question = self._generator.generate(
            user_id=user_id,
            concept_id=target.concept_id,
            concept_name=target.concept_name,
            objective=target.objective,
            bloom_level=target.bloom_level,
            difficulty=target.difficulty,
            mastery_score=target.mastery_score,
        )
        question.purpose = f"{question.purpose} ({target.reason})"
        question.mark_asked(now=now)
        return await self._questions.create(question)

    async def submit_answer(
        self, user_id: UUID, question_id: UUID, answer: str, now: datetime | None = None
    ) -> SubmissionResult:
        now = now or datetime.now(UTC)

        question = await self._questions.get_by_id(question_id)
        if question is None:
            raise QuestionOwnershipError("Question not found")
        if question.user_id != user_id:
            raise QuestionOwnershipError("Question does not belong to this user")

        evaluation = self._evaluator.evaluate(question, answer)
        question.record_evaluation(answer, evaluation, now=now)
        await self._questions.update(question)

        evidence: LearnerEvidence | None = None
        try:
            evidence = await self._confidence.apply_question_result(question)
        except Exception as exc:  # fail-open: evaluation still returns to the user
            logger.error("question_confidence_update_failed", question_id=str(question_id), error=str(exc))

        confidence_after = evidence.confidence_after if evidence else 0.0
        return SubmissionResult(
            question=question,
            evaluation=evaluation,
            evidence=evidence,
            confidence_after=confidence_after,
        )

    async def history(
        self, user_id: UUID, status: str | None = None, limit: int = 20
    ) -> list[GeneratedQuestion]:
        return await self._questions.list_by_user(user_id, status=status, limit=limit)
