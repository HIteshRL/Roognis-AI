import structlog
from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models as qmodels
from qdrant_client.http.exceptions import UnexpectedResponse

from src.infrastructure.vector.base import AbstractVectorStore, SearchResult, VectorPoint

logger = structlog.get_logger(__name__)


class QdrantVectorStore(AbstractVectorStore):
    def __init__(self, url: str, collection: str, api_key: str = "") -> None:
        self._client = AsyncQdrantClient(url=url, api_key=api_key or None)
        self._collection = collection

    @property
    def provider_name(self) -> str:
        return "qdrant"

    async def ensure_collection(self, dimension: int) -> None:
        try:
            await self._client.get_collection(self._collection)
        except (UnexpectedResponse, Exception):
            logger.info("qdrant_creating_collection", collection=self._collection, dim=dimension)
            await self._client.create_collection(
                collection_name=self._collection,
                vectors_config=qmodels.VectorParams(
                    size=dimension,
                    distance=qmodels.Distance.COSINE,
                ),
            )

    async def upsert(self, points: list[VectorPoint]) -> None:
        qdrant_points = [
            qmodels.PointStruct(id=p.id, vector=p.vector, payload=p.payload) for p in points
        ]
        await self._client.upsert(collection_name=self._collection, points=qdrant_points)

    async def search(
        self,
        query_vector: list[float],
        top_k: int,
        score_threshold: float,
        filter_payload: dict | None = None,
    ) -> list[SearchResult]:
        qdrant_filter = None
        if filter_payload:
            conditions = [
                qmodels.FieldCondition(
                    key=k, match=qmodels.MatchValue(value=v)
                )
                for k, v in filter_payload.items()
            ]
            qdrant_filter = qmodels.Filter(must=conditions)

        results = await self._client.search(
            collection_name=self._collection,
            query_vector=query_vector,
            limit=top_k,
            score_threshold=score_threshold,
            query_filter=qdrant_filter,
            with_payload=True,
        )
        return [
            SearchResult(id=str(r.id), score=r.score, payload=r.payload or {})
            for r in results
        ]

    async def delete_by_payload(self, filter_payload: dict) -> None:
        conditions = [
            qmodels.FieldCondition(key=k, match=qmodels.MatchValue(value=v))
            for k, v in filter_payload.items()
        ]
        await self._client.delete(
            collection_name=self._collection,
            points_selector=qmodels.FilterSelector(
                filter=qmodels.Filter(must=conditions)
            ),
        )

    async def collection_stats(self) -> dict:
        info = await self._client.get_collection(self._collection)
        return {
            "collection": self._collection,
            "vectors_count": info.vectors_count,
            "points_count": info.points_count,
            "status": str(info.status),
        }
