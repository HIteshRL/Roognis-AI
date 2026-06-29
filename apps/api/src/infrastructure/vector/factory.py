from functools import lru_cache

from src.config import get_settings
from src.infrastructure.vector.base import AbstractVectorStore


@lru_cache
def get_vector_store() -> AbstractVectorStore:
    settings = get_settings()
    from src.infrastructure.vector.qdrant_store import QdrantVectorStore

    return QdrantVectorStore(
        url=settings.qdrant_url,
        collection=settings.qdrant_collection,
        api_key=settings.qdrant_api_key,
    )
