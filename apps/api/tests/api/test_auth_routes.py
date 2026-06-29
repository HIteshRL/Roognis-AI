import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport

from src.application.dtos.user import UserResponse
from datetime import datetime


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
    with patch("src.application.interfaces.dependencies.get_auth_service") as mock_factory:
        mock_service = AsyncMock()
        mock_service.register.return_value = (_mock_user_response(), "test-token")
        mock_factory.return_value = mock_service

        from src.main import app

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/auth/register",
                json={"email": "test@example.com", "username": "testuser", "password": "password123"},
            )

        assert response.status_code == 201
        body = response.json()
        assert body["success"] is True
        assert "request_id" in body
        assert "token" in body["data"]


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


@pytest.mark.asyncio
async def test_me_requires_auth():
    from src.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/auth/me")

    assert response.status_code == 401
