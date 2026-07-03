"""Unit tests for ResponseCacheService — Phase 0.1 semantic RAG response cache."""
import json
from unittest.mock import AsyncMock

import pytest

from src.application.services.response_cache_service import ResponseCacheService


@pytest.fixture
def redis():
    return AsyncMock()


@pytest.fixture
def svc(redis):
    return ResponseCacheService(redis, ttl_seconds=3600)


def test_normalize_query_collapses_whitespace_and_case():
    assert ResponseCacheService.normalize_query("  What   IS\nPhotosynthesis?  ") == "what is photosynthesis?"


def test_build_key_is_stable_for_equivalent_queries(svc):
    key1 = svc.build_key("What is photosynthesis?", {"grade": "9"})
    key2 = svc.build_key("what   is PHOTOSYNTHESIS?", {"grade": "9"})
    assert key1 == key2


def test_build_key_differs_for_different_filters(svc):
    key1 = svc.build_key("What is photosynthesis?", {"grade": "9"})
    key2 = svc.build_key("What is photosynthesis?", {"grade": "10"})
    assert key1 != key2


def test_build_key_filter_order_independent(svc):
    key1 = svc.build_key("q", {"grade": "9", "subject": "Bio"})
    key2 = svc.build_key("q", {"subject": "Bio", "grade": "9"})
    assert key1 == key2


@pytest.mark.asyncio
async def test_get_returns_none_on_cache_miss(svc, redis):
    redis.get.return_value = None
    result = await svc.get("query", {})
    assert result is None


@pytest.mark.asyncio
async def test_get_returns_parsed_payload_on_hit(svc, redis):
    redis.get.return_value = json.dumps({"answer": "42"})
    result = await svc.get("query", {})
    assert result == {"answer": "42"}


@pytest.mark.asyncio
async def test_get_fails_open_on_redis_error(svc, redis):
    redis.get.side_effect = Exception("connection refused")
    result = await svc.get("query", {})
    assert result is None


@pytest.mark.asyncio
async def test_set_writes_with_ttl(svc, redis):
    await svc.set("query", {"grade": "9"}, {"answer": "42"})
    redis.set.assert_called_once()
    _, kwargs = redis.set.call_args
    assert kwargs.get("ex") == 3600


@pytest.mark.asyncio
async def test_set_fails_open_on_redis_error(svc, redis):
    redis.set.side_effect = Exception("connection refused")
    # Should not raise
    await svc.set("query", {}, {"answer": "42"})
