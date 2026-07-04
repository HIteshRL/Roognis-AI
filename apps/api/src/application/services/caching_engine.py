"""
CachingEngine — the Cache & FAQ Intelligence tier (ADR-012).

Composes: Query Normalizer + Semantic Hash + Hot Query Detector + Cache Policy
Manager + Cache Invalidation Controller + FAQ Knowledge Base promotion, over a
Redis in-memory cache. Drop-in for ResponseCacheService on the RAG path
(same get/set contract). Fail-open everywhere: Redis or FAQ failures never
break answering — the cache is a latency optimization, not a correctness path.
"""
import contextlib
import json
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager

import redis.asyncio as aioredis
import structlog

from src.application.services.query_normalizer import QueryNormalizer
from src.domain.entities.faq import FaqEntry
from src.domain.repositories.faq_repository import AbstractFaqRepository

logger = structlog.get_logger(__name__)

_ANSWER_PREFIX = "cache:ans:"
_HITS_PREFIX = "cache:hits:"
_VER_PREFIX = "cache:ver:"

# A factory that yields a FAQ repository bound to a FRESH, isolated DB session.
# FAQ promotion must never share the RAG request's session — a failed write there
# would poison the request transaction and 500 the answer (ADR-012 fail-open).
FaqWriter = Callable[[], AbstractAsyncContextManager[AbstractFaqRepository]]


class CachingEngine:
    def __init__(
        self,
        redis: aioredis.Redis | None,
        faq_repo: AbstractFaqRepository | None = None,
        faq_writer: FaqWriter | None = None,
        default_ttl: int = 3600,
        hot_ttl: int = 86400,
        hot_threshold: int = 3,
        faq_promote_threshold: int = 5,
    ) -> None:
        self._redis = redis
        self._faq = faq_repo  # read-only (stats); reads share the request session
        self._faq_writer = faq_writer  # writes on their own isolated session
        self._default_ttl = default_ttl
        self._hot_ttl = hot_ttl
        self._hot_threshold = hot_threshold
        self._faq_threshold = faq_promote_threshold

    # ── Public get/set (ResponseCacheService-compatible) ──────────────────────

    async def get(self, query: str, scope: dict | None) -> dict | None:
        if not self._redis:
            return None
        version = await self._ns_version(scope)
        key = QueryNormalizer.semantic_hash(query, scope, version)
        try:
            raw = await self._redis.get(f"{_ANSWER_PREFIX}{key}")
        except Exception as exc:
            logger.warning("cache_read_failed", error=str(exc))
            return None
        if not raw:
            return None
        try:
            payload = json.loads(raw)
        except (TypeError, ValueError):
            return None
        await self._on_hit(key, query, scope, payload)
        return payload

    async def set(self, query: str, scope: dict | None, payload: dict) -> None:
        if not self._redis:
            return
        version = await self._ns_version(scope)
        key = QueryNormalizer.semantic_hash(query, scope, version)
        try:
            await self._redis.set(
                f"{_ANSWER_PREFIX}{key}", json.dumps(payload), ex=self._default_ttl
            )
        except Exception as exc:
            logger.warning("cache_write_failed", error=str(exc))

    # ── Hot Query Detector + Cache Policy + FAQ promotion ─────────────────────

    async def _on_hit(self, key: str, query: str, scope: dict | None, payload: dict) -> None:
        try:
            count = await self._redis.incr(f"{_HITS_PREFIX}{key}")
        except Exception:
            return
        # Bound the counter's lifetime so cold keys don't leak Redis memory forever.
        if count == 1:
            with contextlib.suppress(Exception):
                await self._redis.expire(f"{_HITS_PREFIX}{key}", self._hot_ttl)
        # Policy Manager: promote a hot key to a longer TTL.
        if count == self._hot_threshold:
            with contextlib.suppress(Exception):
                await self._redis.expire(f"{_ANSWER_PREFIX}{key}", self._hot_ttl)
        # FAQ Knowledge Base: promote at threshold, then refresh periodically.
        if self._faq_writer and (count == self._faq_threshold or count % 10 == 0):
            await self._promote_faq(key, query, scope, payload, count)

    async def _promote_faq(
        self, key: str, query: str, scope: dict | None, payload: dict, count: int
    ) -> None:
        answer = payload.get("answer")
        if not answer or not self._faq_writer:
            return
        scope = scope or {}
        entry = FaqEntry(
            cache_key=key,
            question=payload.get("query", query),
            answer=answer,
            normalized_query=QueryNormalizer.normalize(query),
            subject=scope.get("subject"),
            grade=scope.get("grade"),
            hit_count=count,
        )
        # Isolated session: a failure here rolls back on its own and never
        # touches the RAG request transaction that triggered the hit.
        try:
            async with self._faq_writer() as repo:
                await repo.upsert_hit(entry)
        except Exception as exc:
            logger.warning("faq_promote_failed", error=str(exc))

    # ── Cache Invalidation Controller ─────────────────────────────────────────

    async def invalidate_scope(self, subject: str | None) -> int:
        """Bump the namespace version so all keys in this scope are orphaned."""
        if not self._redis:
            return 0
        try:
            return await self._redis.incr(f"{_VER_PREFIX}{subject or 'global'}")
        except Exception as exc:
            logger.warning("cache_invalidate_failed", error=str(exc))
            return 0

    async def _ns_version(self, scope: dict | None) -> int:
        if not self._redis:
            return 1
        subject = (scope or {}).get("subject") or "global"
        try:
            raw = await self._redis.get(f"{_VER_PREFIX}{subject}")
            return int(raw) if raw else 0
        except Exception:
            return 0

    # ── Stats ─────────────────────────────────────────────────────────────────

    async def stats(self) -> dict:
        redis_ok = False
        if self._redis:
            try:
                redis_ok = bool(await self._redis.ping())
            except Exception:
                redis_ok = False
        faq_count = 0
        if self._faq:
            try:
                faq_count = await self._faq.count()
            except Exception:
                faq_count = 0
        return {
            "redis_available": redis_ok,
            "faq_entries": faq_count,
            "default_ttl_seconds": self._default_ttl,
            "hot_ttl_seconds": self._hot_ttl,
            "hot_threshold": self._hot_threshold,
            "faq_promote_threshold": self._faq_threshold,
        }
