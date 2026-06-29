import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient, ASGITransport

os.environ.setdefault("API_SECRET_KEY", "test-secret-key-that-is-at-least-32-chars-long")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("GROQ_API_KEY", "test-key")

from src.infrastructure.logging.setup import configure_logging

configure_logging("INFO", "console")


@pytest.mark.asyncio
async def test_health_endpoint_degraded_when_db_down():
    """Health endpoint returns 200 even when DB is down — status field shows 'degraded'."""
    from src.main import app
    from src.infrastructure.database import session as db_session
    from src.infrastructure.cache import redis_client

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(side_effect=Exception("DB down"))
    mock_session.commit = AsyncMock()
    mock_session.rollback = AsyncMock()
    mock_session.close = AsyncMock()

    async def mock_get_db():
        yield mock_session

    mock_redis = AsyncMock()
    mock_redis.ping = AsyncMock(return_value=True)

    app.dependency_overrides[db_session.get_db] = mock_get_db
    redis_client._redis = mock_redis

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/health")
    finally:
        app.dependency_overrides.clear()
        redis_client._redis = None

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert "request_id" in body
    assert body["data"]["status"] == "degraded"
    assert body["data"]["database"] == "down"
    assert body["data"]["cache"] == "up"


@pytest.mark.asyncio
async def test_version_endpoint():
    from src.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/version")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["version"] == "0.1.0"
    assert body["data"]["env"] == "development"
    assert "request_id" in body


@pytest.mark.asyncio
async def test_request_id_header_present():
    """Every response must carry X-Request-ID header."""
    from src.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/version")

    assert "x-request-id" in response.headers
