from functools import cached_property

import structlog

from src.infrastructure.embeddings.base import AbstractEmbeddingProvider, EmbeddingResult

logger = structlog.get_logger(__name__)


class FastEmbedProvider(AbstractEmbeddingProvider):
    """
    Local embedding using fastembed (ONNX-based, no GPU required, no API key).
    Default model: BAAI/bge-small-en-v1.5 — dimension 384, 33 MB.
    """

    def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5") -> None:
        self._model_name = model_name
        self._dim = 384

    @cached_property
    def _model(self):
        from fastembed import TextEmbedding

        logger.info("fastembed_model_loading", model=self._model_name)
        return TextEmbedding(model_name=self._model_name)

    @property
    def provider_name(self) -> str:
        return "fastembed"

    @property
    def dimension(self) -> int:
        return self._dim

    async def embed(self, texts: list[str]) -> EmbeddingResult:
        vectors = list(self._model.embed(texts))
        return EmbeddingResult(
            vectors=[v.tolist() for v in vectors],
            model=self._model_name,
            dimension=self._dim,
        )

    async def embed_query(self, text: str) -> list[float]:
        result = await self.embed([text])
        return result.vectors[0]
