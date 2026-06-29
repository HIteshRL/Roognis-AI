import os
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport

os.environ.setdefault("API_SECRET_KEY", "test-secret-key-that-is-at-least-32-chars-long")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("GROQ_API_KEY", "test-key")

from src.application.dtos.user import UserResponse
from src.infrastructure.logging.setup import configure_logging

configure_logging("INFO", "console")


def _mock_user_response():
    return UserResponse(
        id="123e4567-e89b-12d3-a456-426614174000",
        email="test@example.com",
        username="testuser",
        is_active=True,
        is_verified=False,
        created_at=datetime.utcnow().isoformat(),
        updated_at=datetime.utcnow().isoformat(),
    )


@pytest.mark.asyncio
async def test_register_returns_structured_response():
    from src.main import app
    from src.application.interfaces import dependencies

    mock_service = AsyncMock()
    mock_service.register = AsyncMock(return_value=(_mock_user_response(), "test-token"))

    app.dependency_overrides[dependencies.get_auth_service] = lambda: mock_service

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/auth/register",
                json={"email": "test@example.com", "username": "testuser", "password": "password123"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201
    body = response.json()
    assert body["success"] is True
    assert "request_id" in body
    assert "token" in body["data"]
    assert body["data"]["token"] == "test-token"


@pytest.mark.asyncio
async def test_login_invalid_body():
    from src.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "not-an-email", "password": ""},
        )

    assert response.status_code == 422
    body = response.json()
    assert body["success"] is False
    assert "request_id" in body


@pytest.mark.asyncio
async def test_me_requires_auth():
    from src.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/auth/me")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_response_envelope_shape():
    """Every response must contain success, data, message, request_id."""
    from src.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/version")

    body = response.json()
    assert "success" in body
    assert "data" in body
    assert "message" in body
    assert "request_id" in body
    assert body["success"] is True
    assert body["data"]["version"] == "0.2.0"

