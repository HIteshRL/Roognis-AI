from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class VectorPoint:
    id: str
    vector: list[float]
    payload: dict = field(default_factory=dict)


@dataclass
class SearchResult:
    id: str
    score: float
    payload: dict = field(default_factory=dict)


class AbstractVectorStore(ABC):
    @abstractmethod
    async def ensure_collection(self, dimension: int) -> None:
        """Create the collection if it does not exist."""
        ...

    @abstractmethod
    async def upsert(self, points: list[VectorPoint]) -> None: ...

    @abstractmethod
    async def search(
        self,
        query_vector: list[float],
        top_k: int,
        score_threshold: float,
        filter_payload: dict | None = None,
    ) -> list[SearchResult]: ...

    @abstractmethod
    async def delete_by_payload(self, filter_payload: dict) -> None: ...

    @abstractmethod
    async def collection_stats(self) -> dict: ...

    @property
    @abstractmethod
    def provider_name(self) -> str: ...
