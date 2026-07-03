from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.entities.quiz import Quiz, QuizAttempt, QuizQuestion, QuizResponse


class AbstractQuizRepository(ABC):
    @abstractmethod
    async def create(self, quiz: Quiz) -> Quiz: ...

    @abstractmethod
    async def get_by_id(self, quiz_id: UUID) -> Quiz | None: ...

    @abstractmethod
    async def list_by_user(
        self, user_id: UUID, subject: str | None, limit: int, offset: int
    ) -> list[Quiz]: ...

    @abstractmethod
    async def count_by_user(self, user_id: UUID, subject: str | None = None) -> int: ...

    @abstractmethod
    async def update(self, quiz: Quiz) -> Quiz: ...

    @abstractmethod
    async def delete(self, quiz_id: UUID) -> None: ...


class AbstractQuizQuestionRepository(ABC):
    @abstractmethod
    async def create_many(self, questions: list[QuizQuestion]) -> list[QuizQuestion]: ...

    @abstractmethod
    async def list_by_quiz(self, quiz_id: UUID) -> list[QuizQuestion]: ...


class AbstractQuizAttemptRepository(ABC):
    @abstractmethod
    async def create(self, attempt: QuizAttempt) -> QuizAttempt: ...

    @abstractmethod
    async def get_by_id(self, attempt_id: UUID) -> QuizAttempt | None: ...

    @abstractmethod
    async def list_by_user(
        self, user_id: UUID, limit: int, offset: int
    ) -> list[QuizAttempt]: ...

    @abstractmethod
    async def update(self, attempt: QuizAttempt) -> QuizAttempt: ...


class AbstractQuizResponseRepository(ABC):
    @abstractmethod
    async def create(self, response: QuizResponse) -> QuizResponse: ...

    @abstractmethod
    async def list_by_attempt(self, attempt_id: UUID) -> list[QuizResponse]: ...
