import os
import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from datetime import datetime

# Override environment before importing app modules
os.environ.setdefault("API_SECRET_KEY", "test-secret-key-that-is-at-least-32-chars-long")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("GROQ_API_KEY", "test-key")

from src.infrastructure.logging.setup import configure_logging
configure_logging("WARNING", "console")
os.environ.setdefault("GROQ_API_KEY", "test-groq-key")

from src.domain.entities.user import User
from src.domain.entities.profile import Profile, Settings
from src.domain.entities.conversation import Conversation, Message


@pytest.fixture
def user_id():
    return uuid4()


@pytest.fixture
def sample_user(user_id):
    return User(
        id=user_id,
        email="test@example.com",
        username="testuser",
        password_hash="$2b$12$hashed",
        is_active=True,
        is_verified=False,
    )


@pytest.fixture
def sample_profile(user_id):
    return Profile(user_id=user_id)


@pytest.fixture
def sample_settings(user_id):
    return Settings(user_id=user_id)


@pytest.fixture
def sample_conversation(user_id):
    return Conversation(user_id=user_id, title="Test conversation")


@pytest.fixture
def sample_message(sample_conversation):
    return Message(
        conversation_id=sample_conversation.id,
        role="user",
        content="Hello, world!",
    )


@pytest.fixture
def mock_user_repo():
    repo = AsyncMock()
    return repo


@pytest.fixture
def mock_profile_repo():
    return AsyncMock()


@pytest.fixture
def mock_settings_repo():
    return AsyncMock()


@pytest.fixture
def mock_conversation_repo():
    return AsyncMock()


@pytest.fixture
def mock_message_repo():
    return AsyncMock()


@pytest.fixture
def mock_llm_provider():
    provider = AsyncMock()
    provider.provider_name = "mock"
    return provider


@pytest.fixture
def mock_prompt_loader():
    loader = AsyncMock()
    loader.get = AsyncMock(return_value="You are a helpful assistant.")
    return loader
