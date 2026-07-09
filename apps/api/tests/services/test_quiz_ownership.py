"""Quiz attempts must verify ownership before creating.

Without the check, a user who obtains another user's quiz UUID could start
their own attempt and then read that quiz's questions, correct answers, and
explanations via the results endpoint.
"""
from uuid import uuid4

import pytest

from src.application.services.quiz_service import QuizService
from src.domain.entities.quiz import Quiz, QuizAttempt
from src.domain.exceptions import EntityNotFound


class _FakeQuizRepo:
    def __init__(self, quiz):
        self._quiz = quiz

    async def get_by_id(self, quiz_id):
        return self._quiz


class _FakeAttemptRepo:
    def __init__(self):
        self.created = []

    async def create(self, attempt):
        self.created.append(attempt)
        return attempt


def _service(quiz):
    return QuizService(
        quiz_repo=_FakeQuizRepo(quiz),
        question_repo=None,
        attempt_repo=_FakeAttemptRepo(),
        response_repo=None,
        mastery_repo=None,
        concept_repo=None,
    )


@pytest.mark.asyncio
async def test_start_attempt_rejects_foreign_quiz():
    owner, attacker = uuid4(), uuid4()
    quiz = Quiz(user_id=owner, title="Fractions quiz", subject="Math", chapter="Fractions")
    svc = _service(quiz)

    with pytest.raises(EntityNotFound):
        await svc.start_attempt(attacker, quiz.id)


@pytest.mark.asyncio
async def test_start_attempt_rejects_missing_quiz():
    svc = _service(None)
    with pytest.raises(EntityNotFound):
        await svc.start_attempt(uuid4(), uuid4())


@pytest.mark.asyncio
async def test_start_attempt_allows_owner():
    owner = uuid4()
    quiz = Quiz(user_id=owner, title="Fractions quiz", subject="Math", chapter="Fractions")
    svc = _service(quiz)

    attempt = await svc.start_attempt(owner, quiz.id)
    assert isinstance(attempt, QuizAttempt)
    assert attempt.user_id == owner
    assert attempt.quiz_id == quiz.id
