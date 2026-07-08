"""Unit tests for the Cache & FAQ Intelligence engine (ADR-012) — fake Redis."""
from contextlib import asynccontextmanager

import pytest

from src.application.services.caching_engine import CachingEngine
from src.application.services.query_normalizer import QueryNormalizer


def _writer_for(repo):
    """Build a faq_writer factory that yields the given fake repo (no real session)."""

    @asynccontextmanager
    async def _writer():
        yield repo

    return _writer


class _FakeRedis:
    def __init__(self):
        self.kv: dict[str, str] = {}
        self.ttl: dict[str, int] = {}

    async def get(self, key):
        return self.kv.get(key)

    async def set(self, key, value, ex=None):
        self.kv[key] = value
        if ex is not None:
            self.ttl[key] = ex

    async def incr(self, key):
        val = int(self.kv.get(key, 0)) + 1
        self.kv[key] = str(val)
        return val

    async def expire(self, key, ttl):
        self.ttl[key] = ttl

    async def ping(self):
        return True


class _FakeFaqRepo:
    def __init__(self):
        self.rows: dict[str, object] = {}

    async def get_by_cache_key(self, cache_key):
        return self.rows.get(cache_key)

    async def upsert_hit(self, entry):
        self.rows[entry.cache_key] = entry
        return entry

    async def list_top(self, subject, limit):
        return list(self.rows.values())[:limit]

    async def search(self, term, limit):
        return []

    async def count(self):
        return len(self.rows)


# ── Normalizer ───────────────────────────────────────────────────────────────


def test_normalize_collapses_variance():
    assert QueryNormalizer.normalize("  What IS  Photosynthesis??? ") == "what is photosynthesis"
    assert QueryNormalizer.normalize("What is photosynthesis") == QueryNormalizer.normalize(
        "what is    PHOTOSYNTHESIS!"
    )


def test_semantic_hash_scope_and_version_sensitive():
    a = QueryNormalizer.semantic_hash("q", {"subject": "Bio"}, 1)
    b = QueryNormalizer.semantic_hash("q", {"subject": "Bio"}, 1)
    c = QueryNormalizer.semantic_hash("q", {"subject": "Chem"}, 1)
    d = QueryNormalizer.semantic_hash("q", {"subject": "Bio"}, 2)
    assert a == b
    assert a != c
    assert a != d


# ── Engine ───────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_set_roundtrip():
    engine = CachingEngine(redis=_FakeRedis(), faq_repo=_FakeFaqRepo())
    scope = {"subject": "Bio"}
    assert await engine.get("what is a cell", scope) is None
    await engine.set("what is a cell", scope, {"query": "what is a cell", "answer": "A unit."})
    hit = await engine.get("What is a CELL?", scope)  # normalization → same key
    assert hit is not None
    assert hit["answer"] == "A unit."


@pytest.mark.asyncio
async def test_hot_query_promotes_to_faq():
    faq = _FakeFaqRepo()
    engine = CachingEngine(
        redis=_FakeRedis(),
        faq_repo=faq,
        faq_writer=_writer_for(faq),
        hot_threshold=2,
        faq_promote_threshold=3,
    )
    scope = {"subject": "Bio"}
    await engine.set("q1", scope, {"query": "q1", "answer": "ans"})
    for _ in range(3):
        await engine.get("q1", scope)
    assert await faq.count() == 1
    entry = next(iter(faq.rows.values()))
    assert entry.subject == "Bio"
    assert entry.answer == "ans"


@pytest.mark.asyncio
async def test_no_redis_fails_open():
    engine = CachingEngine(redis=None, faq_repo=_FakeFaqRepo())
    assert await engine.get("q", None) is None
    await engine.set("q", None, {"answer": "x"})  # no-op, must not raise
    assert (await engine.stats())["redis_available"] is False


@pytest.mark.asyncio
async def test_invalidation_orphans_prior_answer():
    engine = CachingEngine(redis=_FakeRedis(), faq_repo=_FakeFaqRepo())
    scope = {"subject": "Bio"}
    await engine.set("q", scope, {"query": "q", "answer": "old"})
    assert (await engine.get("q", scope))["answer"] == "old"
    await engine.invalidate_scope("Bio")
    assert await engine.get("q", scope) is None  # version bumped → new key, miss
