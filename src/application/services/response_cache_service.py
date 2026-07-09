"""
Semantic response cache for stateless RAG queries — Phase 0.1 fix.

Normalizes and hashes the (query + curriculum filter) pair so two students
asking the same question in slightly different phrasing don't both pay for
an LLM call. Redis-backed, TTL-bound. Cache misses and Redis outages both
fail open — this is a latency optimization, never a correctness dependency.
"""
import hashlib
import json
import re

import redis.asyncio as aioredis
import structlog

logger = structlog.get_logger(__name__)

_CACHE_PREFIX = "rag:response:"
_DEFAULT_TTL_SECONDS = 3600
_WHITESPACE_RE = re.compile(r"\s+")


class ResponseCacheService:
    def __init__(self, redis: aioredis.Redis, ttl_seconds: int = _DEFAULT_TTL_SECONDS) -> None:
        self._redis = redis
        self._ttl = ttl_seconds

    @staticmethod
    def normalize_query(query: str) -> str:
        return _WHITESPACE_RE.sub(" ", query.strip().lower())

    def build_key(self, query: str, curriculum_filter: dict | None) -> str:
        normalized = self.normalize_query(query)
        filter_json = json.dumps(curriculum_filter or {}, sort_keys=True)
        digest = hashlib.sha256(f"{normalized}|{filter_json}".encode()).hexdigest()
        return f"{_CACHE_PREFIX}{digest}"

    async def get(self, query: str, curriculum_filter: dict | None) -> dict | None:
        key = self.build_key(query, curriculum_filter)
        try:
            raw = await self._redis.get(key)
        except Exception as exc:
            logger.warning("response_cache_read_failed", error=str(exc))
            return None
        if not raw:
            return None
        try:
            return json.loads(raw)
        except (TypeError, ValueError):
            return None

    async def set(self, query: str, curriculum_filter: dict | None, payload: dict) -> None:
        key = self.build_key(query, curriculum_filter)
        try:
            await self._redis.set(key, json.dumps(payload), ex=self._ttl)
        except Exception as exc:
            logger.warning("response_cache_write_failed", error=str(exc))
