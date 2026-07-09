import structlog
from openai import AsyncOpenAI

from src.infrastructure.embeddings.base import AbstractEmbeddingProvider, EmbeddingResult

logger = structlog.get_logger(__name__)

_DIMENSIONS: dict[str, int] = {
    "text-embedding-3-small": 1536,
    "text-embedding-3-large": 3072,
    "text-embedding-ada-002": 1536,
}


class OpenAIEmbeddingProvider(AbstractEmbeddingProvider):
    def __init__(self, api_key: str, model: str = "text-embedding-3-small") -> None:
        self._client = AsyncOpenAI(api_key=api_key)
        self._model = model
        self._dim = _DIMENSIONS.get(model, 1536)

    @property
    def provider_name(self) -> str:
        return "openai"

    @property
    def dimension(self) -> int:
        return self._dim

    @property
    def max_tokens(self) -> int:
        # text-embedding-3-* accept up to 8191 tokens.
        return 8191

    async def embed(self, texts: list[str]) -> EmbeddingResult:
        response = await self._client.embeddings.create(input=texts, model=self._model)
        vectors = [item.embedding for item in response.data]
        return EmbeddingResult(vectors=vectors, model=self._model, dimension=self._dim)

    async def embed_query(self, text: str) -> list[float]:
        result = await self.embed([text])
        return result.vectors[0]
