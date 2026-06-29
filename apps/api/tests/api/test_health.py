import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import AsyncClient, ASGITransport


@pytest.mark.asyncio
async def test_health_endpoint():
    with (
        patch("src.infrastructure.database.session.get_db") as mock_db,
        patch("src.infrastructure.cache.redis_client.get_redis") as mock_redis,
    ):
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=MagicMock())
        mock_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_db.return_value.__aexit__ = AsyncMock(return_value=False)

        mock_redis_client = AsyncMock()
        mock_redis_client.ping = AsyncMock(return_value=True)
        mock_redis.return_value = mock_redis_client

        from src.main import app

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/health")

        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert "request_id" in body


@pytest.mark.asyncio
async def test_version_endpoint():
    from src.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/version")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert "version" in body["data"]
