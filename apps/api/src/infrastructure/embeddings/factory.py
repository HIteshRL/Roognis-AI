from functools import lru_cache

from src.config import get_settings
from src.infrastructure.embeddings.base import AbstractEmbeddingProvider


@lru_cache
def get_embedding_provider() -> AbstractEmbeddingProvider:
    settings = get_settings()

    if settings.embedding_provider == "openai":
        from src.infrastructure.embeddings.openai_provider import OpenAIEmbeddingProvider

        return OpenAIEmbeddingProvider(
            api_key=settings.openai_api_key,
            model=settings.openai_embedding_model,
        )

    from src.infrastructure.embeddings.fastembed_provider import FastEmbedProvider

    return FastEmbedProvider(model_name=settings.embedding_model)
