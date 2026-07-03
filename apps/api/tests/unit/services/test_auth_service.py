from unittest.mock import AsyncMock

import pytest

from src.application.dtos.auth import LoginRequest, RegisterRequest
from src.application.services.auth_service import AuthService
from src.config import get_settings
from src.domain.exceptions import AuthenticationError, DuplicateEntity


@pytest.fixture
def auth_service(mock_user_repo, mock_profile_repo, mock_settings_repo):
    return AuthService(
        user_repo=mock_user_repo,
        profile_repo=mock_profile_repo,
        settings_repo=mock_settings_repo,
        app_settings=get_settings(),
    )


@pytest.mark.asyncio
async def test_register_success(auth_service, mock_user_repo, mock_profile_repo, mock_settings_repo, sample_user):
    mock_user_repo.get_by_email.return_value = None
    mock_user_repo.get_by_username.return_value = None
    mock_user_repo.create.return_value = sample_user
    mock_profile_repo.create.return_value = AsyncMock()
    mock_settings_repo.create.return_value = AsyncMock()

    dto = RegisterRequest(email="test@example.com", username="testuser", password="password123")
    user_resp, token = await auth_service.register(dto)

    assert user_resp.email == "test@example.com"
    assert token != ""
    mock_user_repo.create.assert_called_once()


@pytest.mark.asyncio
async def test_register_duplicate_email(auth_service, mock_user_repo, sample_user):
    mock_user_repo.get_by_email.return_value = sample_user

    dto = RegisterRequest(email="test@example.com", username="testuser", password="password123")
    with pytest.raises(DuplicateEntity, match="Email already registered"):
        await auth_service.register(dto)


@pytest.mark.asyncio
async def test_login_success(auth_service, mock_user_repo, sample_user):
    from passlib.context import CryptContext
    ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
    sample_user.password_hash = ctx.hash("password123")
    mock_user_repo.get_by_email.return_value = sample_user

    dto = LoginRequest(email="test@example.com", password="password123")
    user_resp, token = await auth_service.login(dto)

    assert user_resp.email == "test@example.com"
    assert token != ""


@pytest.mark.asyncio
async def test_login_wrong_password(auth_service, mock_user_repo, sample_user):
    from passlib.context import CryptContext
    ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
    sample_user.password_hash = ctx.hash("correct-password")
    mock_user_repo.get_by_email.return_value = sample_user

    dto = LoginRequest(email="test@example.com", password="wrong-password")
    with pytest.raises(AuthenticationError):
        await auth_service.login(dto)


@pytest.mark.asyncio
async def test_login_user_not_found(auth_service, mock_user_repo):
    mock_user_repo.get_by_email.return_value = None

    dto = LoginRequest(email="nobody@example.com", password="password123")
    with pytest.raises(AuthenticationError):
        await auth_service.login(dto)


@pytest.mark.asyncio
async def test_get_current_user_invalid_token(auth_service):
    with pytest.raises(AuthenticationError):
        await auth_service.get_current_user("not.a.valid.token")
