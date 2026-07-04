from abc import ABC, abstractmethod

from src.domain.entities.faq import FaqEntry


class AbstractFaqRepository(ABC):
    @abstractmethod
    async def get_by_cache_key(self, cache_key: str) -> FaqEntry | None: ...

    @abstractmethod
    async def upsert_hit(self, entry: FaqEntry) -> FaqEntry:
        """Insert a new FAQ entry or bump hit_count/last_hit_at if it exists."""
        ...

    @abstractmethod
    async def list_top(self, subject: str | None, limit: int) -> list[FaqEntry]: ...

    @abstractmethod
    async def search(self, term: str, limit: int) -> list[FaqEntry]: ...

    @abstractmethod
    async def count(self) -> int: ...
