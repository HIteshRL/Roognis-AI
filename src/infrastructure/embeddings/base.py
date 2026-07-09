from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class EmbeddingResult:
    vectors: list[list[float]]
    model: str
    dimension: int


class AbstractEmbeddingProvider(ABC):
    @abstractmethod
    async def embed(self, texts: list[str]) -> EmbeddingResult: ...

    @abstractmethod
    async def embed_query(self, text: str) -> list[float]: ...

    @property
    @abstractmethod
    def provider_name(self) -> str: ...

    @property
    @abstractmethod
    def dimension(self) -> int: ...
