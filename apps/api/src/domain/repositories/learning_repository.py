from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID

from src.domain.entities.learning import (
    ConceptEdge,
    ConceptMemory,
    ConceptNode,
    LearningGap,
    LearningSession,
    MasteryRecord,
    StudentProfile,
)


class AbstractStudentProfileRepository(ABC):
    @abstractmethod
    async def create(self, profile: StudentProfile) -> StudentProfile: ...

    @abstractmethod
    async def get_by_user_id(self, user_id: UUID) -> StudentProfile | None: ...

    @abstractmethod
    async def update(self, profile: StudentProfile) -> StudentProfile: ...

    @abstractmethod
    async def delete(self, user_id: UUID) -> None: ...


class AbstractLearningSessionRepository(ABC):
    @abstractmethod
    async def create(self, session: LearningSession) -> LearningSession: ...

    @abstractmethod
    async def list_by_user(
        self, user_id: UUID, limit: int, offset: int
    ) -> list[LearningSession]: ...

    @abstractmethod
    async def count_by_user(self, user_id: UUID) -> int: ...

    @abstractmethod
    async def recent_concepts(self, user_id: UUID, days: int) -> list[str]: ...

    @abstractmethod
    async def list_since(self, user_id: UUID, since: datetime) -> list[LearningSession]: ...

    @abstractmethod
    async def session_stats_by_users(
        self, user_ids: list[UUID]
    ) -> dict[UUID, tuple[int, datetime | None]]:
        """Per-user (session_count, last_activity) in one aggregate query."""
        ...


class AbstractConceptNodeRepository(ABC):
    @abstractmethod
    async def get_or_create(self, name: str, subject: str | None, grade: str | None, chapter: str | None) -> ConceptNode: ...

    @abstractmethod
    async def get_by_id(self, concept_id: UUID) -> ConceptNode | None: ...

    @abstractmethod
    async def get_by_name(self, name: str, subject: str | None = None, grade: str | None = None) -> ConceptNode | None: ...

    @abstractmethod
    async def list_by_subject_grade(self, subject: str, grade: str) -> list[ConceptNode]: ...

    @abstractmethod
    async def update(self, node: ConceptNode) -> ConceptNode: ...


class AbstractConceptEdgeRepository(ABC):
    @abstractmethod
    async def create(self, edge: ConceptEdge) -> ConceptEdge: ...

    @abstractmethod
    async def get_prerequisites(self, concept_id: UUID) -> list[ConceptNode]: ...

    @abstractmethod
    async def get_successors(self, concept_id: UUID) -> list[ConceptNode]: ...

    @abstractmethod
    async def exists(self, source_id: UUID, target_id: UUID) -> bool: ...


class AbstractMasteryRepository(ABC):
    @abstractmethod
    async def get_or_create(self, user_id: UUID, concept_id: UUID, concept_name: str) -> MasteryRecord: ...

    @abstractmethod
    async def update(self, record: MasteryRecord) -> MasteryRecord: ...

    @abstractmethod
    async def list_by_user(self, user_id: UUID) -> list[MasteryRecord]: ...

    @abstractmethod
    async def get_by_concept(self, user_id: UUID, concept_id: UUID) -> MasteryRecord | None: ...

    @abstractmethod
    async def average_score(self, user_id: UUID) -> float: ...

    @abstractmethod
    async def average_scores_by_users(self, user_ids: list[UUID]) -> dict[UUID, float]:
        """Per-user average mastery score in one aggregate query."""
        ...


class AbstractLearningGapRepository(ABC):
    @abstractmethod
    async def get_or_create(self, user_id: UUID, concept_id: UUID, concept_name: str, reason: str) -> LearningGap: ...

    @abstractmethod
    async def update(self, gap: LearningGap) -> LearningGap: ...

    @abstractmethod
    async def list_by_user(self, user_id: UUID, include_resolved: bool = False) -> list[LearningGap]: ...

    @abstractmethod
    async def resolve(self, gap_id: UUID) -> None: ...

    @abstractmethod
    async def active_gap_counts_by_users(self, user_ids: list[UUID]) -> dict[UUID, int]:
        """Per-user count of unresolved gaps in one aggregate query."""
        ...

    @abstractmethod
    async def top_concepts_by_users(
        self, user_ids: list[UUID], limit: int = 5
    ) -> list[tuple[str, int]]:
        """Most common unresolved-gap concepts across the cohort, ranked by
        number of distinct students affected."""
        ...


class AbstractConceptMemoryRepository(ABC):
    @abstractmethod
    async def get_or_create(self, user_id: UUID, concept_id: UUID, concept_name: str) -> ConceptMemory: ...

    @abstractmethod
    async def update(self, memory: ConceptMemory) -> ConceptMemory: ...

    @abstractmethod
    async def list_by_user(self, user_id: UUID) -> list[ConceptMemory]: ...

    @abstractmethod
    async def get_by_concept(self, user_id: UUID, concept_id: UUID) -> ConceptMemory | None: ...
