"""
FastAPI dependency providers.
All service construction is here — routes receive fully-constructed services,
never raw infrastructure objects.
"""
from collections.abc import AsyncGenerator
from typing import Annotated

import structlog
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.application.dtos.user import UserResponse
from src.application.services.auth_service import AuthService
from src.application.services.chat_service import ChatService
from src.application.services.user_service import UserService
from src.config import Settings, get_settings
from src.domain.exceptions import AuthenticationError
from src.infrastructure.database.repositories.conversation_repository import (
    ConversationRepository,
    MessageRepository,
)
from src.infrastructure.database.repositories.profile_repository import (
    ProfileRepository,
    SettingsRepository,
)
from src.infrastructure.database.repositories.user_repository import UserRepository
from src.infrastructure.database.session import AsyncSession, get_db
from src.infrastructure.llm.factory import get_llm_provider
from src.infrastructure.llm.prompt_loader import PromptLoader

logger = structlog.get_logger(__name__)
_bearer = HTTPBearer(auto_error=False)


def get_auth_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AuthService:
    return AuthService(
        user_repo=UserRepository(db),
        profile_repo=ProfileRepository(db),
        settings_repo=SettingsRepository(db),
        app_settings=settings,
    )


def get_user_service(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserService:
    return UserService(
        profile_repo=ProfileRepository(db),
        settings_repo=SettingsRepository(db),
    )


def get_chat_service(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ChatService:
    return ChatService(
        conversation_repo=ConversationRepository(db),
        message_repo=MessageRepository(db),
        llm_provider=get_llm_provider(),
        prompt_loader=PromptLoader(db),
    )


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> UserResponse:
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "UNAUTHORIZED", "message": "Authentication required"},
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        return await auth_service.get_current_user(credentials.credentials)
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": e.code, "message": e.message},
            headers={"WWW-Authenticate": "Bearer"},
        ) from e
