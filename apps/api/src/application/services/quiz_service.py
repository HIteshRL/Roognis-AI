from datetime import UTC, datetime
from uuid import UUID

import structlog

from src.application.services.ability_engine import AbilityEngine
from src.domain.entities.learning import MasteryRecord
from src.domain.entities.quiz import Quiz, QuizAttempt, QuizQuestion, QuizResponse
from src.domain.repositories.learning_repository import (
    AbstractConceptNodeRepository,
    AbstractMasteryRepository,
)
from src.domain.repositories.quiz_repository import (
    AbstractQuestionBankRepository,
    AbstractQuizAttemptRepository,
    AbstractQuizQuestionRepository,
    AbstractQuizRepository,
    AbstractQuizResponseRepository,
)

logger = structlog.get_logger(__name__)


class QuizService:
    def __init__(
        self,
        quiz_repo: AbstractQuizRepository,
        question_repo: AbstractQuizQuestionRepository,
        attempt_repo: AbstractQuizAttemptRepository,
        response_repo: AbstractQuizResponseRepository,
        mastery_repo: AbstractMasteryRepository,
        concept_repo: AbstractConceptNodeRepository,
        bank_repo: AbstractQuestionBankRepository | None = None,
        ability_engine: AbilityEngine | None = None,
    ) -> None:
        self._quizzes = quiz_repo
        self._questions = question_repo
        self._attempts = attempt_repo
        self._responses = response_repo
        self._mastery = mastery_repo
        self._concepts = concept_repo
        self._bank = bank_repo
        self._ability = ability_engine

    async def create_quiz(
        self,
        quiz: Quiz,
        questions: list[QuizQuestion],
    ) -> Quiz:
        quiz.question_count = len(questions)
        saved_quiz = await self._quizzes.create(quiz)
        for q in questions:
            q.quiz_id = saved_quiz.id
        await self._questions.create_many(questions)
        logger.info(
            "quiz_created",
            quiz_id=str(saved_quiz.id),
            questions=len(questions),
        )
        return saved_quiz

    async def get_quiz(
        self, quiz_id: UUID, user_id: UUID
    ) -> tuple[Quiz, list[QuizQuestion]] | None:
        quiz = await self._quizzes.get_by_id(quiz_id)
        if not quiz or quiz.user_id != user_id:
            return None
        questions = await self._questions.list_by_quiz(quiz_id)
        return quiz, questions

    async def list_quizzes(
        self,
        user_id: UUID,
        subject: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[Quiz], int]:
        quizzes = await self._quizzes.list_by_user(
            user_id, subject, limit, offset
        )
        total = await self._quizzes.count_by_user(user_id, subject)
        return quizzes, total

    async def start_attempt(
        self, user_id: UUID, quiz_id: UUID
    ) -> QuizAttempt:
        attempt = QuizAttempt(user_id=user_id, quiz_id=quiz_id)
        saved = await self._attempts.create(attempt)
        logger.info(
            "quiz_attempt_started",
            attempt_id=str(saved.id),
            quiz_id=str(quiz_id),
        )
        return saved

    async def submit_and_complete(
        self,
        user_id: UUID,
        quiz_id: UUID,
        attempt_id: UUID,
        responses: list[dict],
    ) -> QuizAttempt:
        questions = await self._questions.list_by_quiz(quiz_id)
        question_map = {q.id: q for q in questions}

        correct_count = 0
        total_time = 0

        for resp in responses:
            q_id = UUID(resp["question_id"])
            question = question_map.get(q_id)
            if not question:
                continue

            is_correct = (
                resp["selected_answer"].strip().lower()
                == question.correct_answer.strip().lower()
            )
            if is_correct:
                correct_count += 1

            time_ms = resp.get("time_spent_ms", 0)
            total_time += time_ms

            quiz_resp = QuizResponse(
                attempt_id=attempt_id,
                question_id=q_id,
                selected_answer=resp["selected_answer"],
                is_correct=is_correct,
                time_spent_ms=time_ms,
            )
            await self._responses.create(quiz_resp)

        total_answered = len(responses)
        score = (correct_count / total_answered) if total_answered > 0 else 0.0

        attempt = await self._attempts.get_by_id(attempt_id)
        if not attempt:
            msg = f"Attempt {attempt_id} not found"
            raise ValueError(msg)

        attempt.score = round(score, 3)
        attempt.correct_count = correct_count
        attempt.total_answered = total_answered
        attempt.total_time_ms = total_time
        attempt.completed_at = datetime.now(UTC)
        attempt = await self._attempts.update(attempt)

        quiz = await self._quizzes.get_by_id(quiz_id)
        if quiz:
            quiz.total_attempts += 1
            if score > quiz.best_score:
                quiz.best_score = round(score, 3)
            quiz.updated_at = datetime.now(UTC)
            await self._quizzes.update(quiz)

        await self._update_mastery(user_id, question_map, responses)

        logger.info(
            "quiz_attempt_completed",
            attempt_id=str(attempt_id),
            score=score,
            correct=correct_count,
            total=total_answered,
        )
        return attempt

    async def get_attempt_results(
        self, attempt_id: UUID, user_id: UUID
    ) -> dict | None:
        attempt = await self._attempts.get_by_id(attempt_id)
        if not attempt or attempt.user_id != user_id:
            return None

        quiz = await self._quizzes.get_by_id(attempt.quiz_id)
        if not quiz:
            return None

        responses = await self._responses.list_by_attempt(attempt_id)
        questions = await self._questions.list_by_quiz(attempt.quiz_id)
        question_map = {q.id: q for q in questions}

        results = []
        for resp in responses:
            q = question_map.get(resp.question_id)
            if not q:
                continue
            results.append({
                "question_id": q.id,
                "question_text": q.question_text,
                "options": q.options,
                "selected_answer": resp.selected_answer,
                "correct_answer": q.correct_answer,
                "is_correct": resp.is_correct,
                "explanation": q.explanation,
                "concept_name": q.concept_name,
            })

        return {
            "attempt": attempt,
            "quiz": quiz,
            "results": results,
        }

    async def quiz_history(
        self, user_id: UUID, limit: int = 10
    ) -> list[dict]:
        attempts = await self._attempts.list_by_user(user_id, limit, 0)
        history = []
        for a in attempts:
            quiz = await self._quizzes.get_by_id(a.quiz_id)
            history.append({
                "attempt": a,
                "quiz_title": quiz.title if quiz else "Unknown",
                "quiz_subject": quiz.subject if quiz else None,
            })
        return history

    async def _update_mastery(
        self,
        user_id: UUID,
        question_map: dict[UUID, QuizQuestion],
        responses: list[dict],
    ) -> None:
        for resp in responses:
            q_id = UUID(resp["question_id"])
            question = question_map.get(q_id)
            if not question or not question.concept_id:
                continue

            is_correct = (
                resp["selected_answer"].strip().lower()
                == question.correct_answer.strip().lower()
            )

            try:
                record = await self._mastery.get_or_create(
                    user_id, question.concept_id, question.concept_name
                )
                record.apply_interaction(
                    question.bloom_level, has_misconception=not is_correct
                )
                # Elo ability update runs in parallel with the mastery score
                # (build-on-top — neither replaces the other), reusing this
                # record's single write.
                await self._apply_ability(record, question, is_correct)
                await self._mastery.update(record)
                logger.debug(
                    "mastery_updated_from_quiz",
                    concept=question.concept_name,
                    correct=is_correct,
                    new_score=record.score,
                    ability=record.ability_rating,
                )
            except Exception as exc:
                logger.warning(
                    "mastery_update_failed",
                    concept=question.concept_name,
                    error=str(exc),
                )

    async def _apply_ability(
        self, record: MasteryRecord, question: QuizQuestion, is_correct: bool
    ) -> None:
        """Nudge the student's per-concept θ and the question's difficulty
        rating against each other (Elo). Fail-open: any issue leaves the
        mastery-score path untouched."""
        if not (self._ability and self._bank and question.bank_question_id):
            return
        try:
            banked = await self._bank.get_by_id(question.bank_question_id)
            if banked is None:
                return
            update = self._ability.update(
                record.ability_rating, banked.difficulty_rating, is_correct
            )
            record.ability_rating = update.student_rating
            banked.difficulty_rating = update.question_rating
            banked.record_outcome(is_correct)
            await self._bank.update_stats(banked)
        except Exception as exc:
            logger.warning("ability_update_failed", error=str(exc))
