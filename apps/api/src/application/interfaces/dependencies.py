"""
FastAPI dependency providers — single source of truth for service construction.
All services are assembled here. Routes receive fully-constructed services.
"""
from functools import lru_cache
from typing import Annotated

import structlog
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.application.dtos.user import UserResponse
from src.application.services.auth_service import AuthService
from src.application.services.chat_service import ChatService
from src.application.services.context_validation_service import ContextValidationService
from src.application.services.document_service import DocumentService
from src.application.services.knowledge_library_service import KnowledgeLibraryService
from src.application.services.prompt_assembly_service import PromptAssemblyService
from src.application.services.retrieval_service import RetrievalService
from src.application.services.search_service import SearchService
from src.application.services.user_service import UserService
from src.application.services.vector_service import VectorService
from src.config import Settings, get_settings
from src.domain.exceptions import AuthenticationError, AuthorizationError
from src.infrastructure.database.repositories.conversation_repository import (
    ConversationRepository,
    MessageRepository,
)
from src.infrastructure.database.repositories.knowledge_repository import (
    ChunkRepository,
    DocumentRepository,
    IngestionJobRepository,
    KnowledgeBaseRepository,
)
from src.infrastructure.database.repositories.profile_repository import (
    ProfileRepository,
    SettingsRepository,
)
from src.infrastructure.database.repositories.user_repository import UserRepository
from src.infrastructure.database.session import AsyncSession, get_db
from src.infrastructure.embeddings.factory import get_embedding_provider
from src.infrastructure.llm.factory import get_llm_provider
from src.infrastructure.llm.prompt_loader import PromptLoader
from src.infrastructure.storage.local_storage import LocalFileStorage
from src.infrastructure.vector.factory import get_vector_store

logger = structlog.get_logger(__name__)
_bearer = HTTPBearer(auto_error=False)


# ── Auth ──────────────────────────────────────────────────────────────────────

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


async def require_admin(
    current_user: Annotated[UserResponse, Depends(get_current_user)],
) -> UserResponse:
    if not getattr(current_user, "is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message": "Admin access required"},
        )
    return current_user


# ── User / Chat ───────────────────────────────────────────────────────────────

def get_user_service(db: Annotated[AsyncSession, Depends(get_db)]) -> UserService:
    return UserService(
        profile_repo=ProfileRepository(db),
        settings_repo=SettingsRepository(db),
    )


def get_chat_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> ChatService:
    prompt_loader = PromptLoader(db)

    if settings.retrieval_enabled:
        vector_store = get_vector_store()
        embedding_provider = get_embedding_provider()
        retrieval_svc = RetrievalService(
            vector_store=vector_store,
            embedding_provider=embedding_provider,
            top_k=settings.retrieval_top_k,
            score_threshold=settings.retrieval_score_threshold,
        )
        prompt_assembly_svc = PromptAssemblyService(prompt_loader)
        context_validation_svc = ContextValidationService(settings.retrieval_score_threshold)
    else:
        retrieval_svc = None
        prompt_assembly_svc = None
        context_validation_svc = None

    return ChatService(
        conversation_repo=ConversationRepository(db),
        message_repo=MessageRepository(db),
        llm_provider=get_llm_provider(),
        prompt_loader=prompt_loader,
        retrieval_svc=retrieval_svc,
        prompt_assembly_svc=prompt_assembly_svc,
        context_validation_svc=context_validation_svc,
        retrieval_enabled=settings.retrieval_enabled,
    )


# ── Knowledge / RAG ───────────────────────────────────────────────────────────

def get_vector_service(
    settings: Annotated[Settings, Depends(get_settings)],
) -> VectorService:
    return VectorService(
        vector_store=get_vector_store(),
        embedding_provider=get_embedding_provider(),
    )


def get_knowledge_library_service(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> KnowledgeLibraryService:
    return KnowledgeLibraryService(
        kb_repo=KnowledgeBaseRepository(db),
        doc_repo=DocumentRepository(db),
    )


def get_document_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    vector_svc: Annotated[VectorService, Depends(get_vector_service)],
) -> DocumentService:
    return DocumentService(
        kb_repo=KnowledgeBaseRepository(db),
        doc_repo=DocumentRepository(db),
        chunk_repo=ChunkRepository(db),
        job_repo=IngestionJobRepository(db),
        storage=LocalFileStorage(settings.storage_local_path),
        vector_svc=vector_svc,
        settings=settings,
    )


def get_search_service(
    settings: Annotated[Settings, Depends(get_settings)],
) -> SearchService:
    embedding_provider = get_embedding_provider()
    retrieval_svc = RetrievalService(
        vector_store=get_vector_store(),
        embedding_provider=embedding_provider,
        top_k=settings.retrieval_top_k,
        score_threshold=settings.retrieval_score_threshold,
    )
    validation_svc = ContextValidationService(settings.retrieval_score_threshold)
    return SearchService(retrieval_svc=retrieval_svc, validation_svc=validation_svc)
