"""
FastAPI dependency providers — single source of truth for service construction.
All services are assembled here. Routes receive fully-constructed services.
"""
from typing import Annotated

import structlog
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.application.dtos.user import UserResponse
from src.application.services.auth_service import AuthService
from src.application.services.chat_service import ChatService
from src.application.services.concept_extraction_service import ConceptExtractionService
from src.application.services.context_validation_service import ContextValidationService
from src.application.services.document_service import DocumentService
from src.application.services.knowledge_graph_service import KnowledgeGraphService
from src.application.services.knowledge_library_service import KnowledgeLibraryService
from src.application.services.learner_behavior_service import LearnerBehaviorService
from src.application.services.learner_context_service import LearnerContextService
from src.application.services.learning_analytics_service import LearningAnalyticsService
from src.application.services.learning_gap_detector import LearningGapDetector
from src.application.services.learning_orchestrator import LearningOrchestrator
from src.application.services.learning_velocity_service import LearningVelocityService
from src.application.services.mastery_engine import MasteryEngine
from src.application.services.next_best_topic_engine import NextBestTopicEngine
from src.application.services.prompt_assembly_service import PromptAssemblyService
from src.application.services.rag_service import RagService
from src.application.services.response_cache_service import ResponseCacheService
from src.application.services.retrieval_service import RetrievalService
from src.application.services.search_service import SearchService
from src.application.services.session_memory_service import SessionMemoryService
from src.application.services.student_profile_service import StudentProfileService
from src.application.services.user_service import UserService
from src.application.services.vector_service import VectorService
from src.config import Settings, get_settings
from src.domain.exceptions import AuthenticationError
from src.infrastructure.cache.redis_client import get_redis
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
from src.infrastructure.database.repositories.learning_repository import (
    ConceptEdgeRepository,
    ConceptNodeRepository,
    LearningGapRepository,
    LearningSessionRepository,
    MasteryRepository,
    StudentProfileRepository,
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

    learner_context_svc = LearnerContextService(
        profile_repo=StudentProfileRepository(db),
        mastery_repo=MasteryRepository(db),
        gap_repo=LearningGapRepository(db),
    )

    return ChatService(
        conversation_repo=ConversationRepository(db),
        message_repo=MessageRepository(db),
        llm_provider=get_llm_provider(),
        prompt_loader=prompt_loader,
        retrieval_svc=retrieval_svc,
        prompt_assembly_svc=prompt_assembly_svc,
        context_validation_svc=context_validation_svc,
        retrieval_enabled=settings.retrieval_enabled,
        learner_context_svc=learner_context_svc,
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


async def get_rag_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> RagService:
    vector_store = get_vector_store()
    embedding_provider = get_embedding_provider()
    retrieval_svc = RetrievalService(
        vector_store=vector_store,
        embedding_provider=embedding_provider,
        top_k=settings.retrieval_top_k,
        score_threshold=settings.retrieval_score_threshold,
    )
    prompt_loader = PromptLoader(db)
    prompt_assembly_svc = PromptAssemblyService(prompt_loader)
    context_validation_svc = ContextValidationService(settings.retrieval_score_threshold)

    response_cache_svc: ResponseCacheService | None = None
    try:
        redis = await get_redis()
        response_cache_svc = ResponseCacheService(redis)
    except Exception as exc:
        logger.warning("response_cache_unavailable", error=str(exc))

    return RagService(
        retrieval_svc=retrieval_svc,
        prompt_assembly_svc=prompt_assembly_svc,
        context_validation_svc=context_validation_svc,
        llm_provider=get_llm_provider(),
        response_cache_svc=response_cache_svc,
    )


# ── Learning Engine ───────────────────────────────────────────────────────────

def get_learning_orchestrator(
    db: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> LearningOrchestrator:
    from groq import AsyncGroq

    node_repo = ConceptNodeRepository(db)
    edge_repo = ConceptEdgeRepository(db)
    mastery_repo = MasteryRepository(db)
    gap_repo = LearningGapRepository(db)
    session_repo = LearningSessionRepository(db)

    groq_client = AsyncGroq(api_key=settings.groq_api_key)
    extractor = ConceptExtractionService(groq_client)
    profile_svc = StudentProfileService(StudentProfileRepository(db))
    session_svc = SessionMemoryService(session_repo)
    mastery_engine = MasteryEngine(mastery_repo=mastery_repo, concept_repo=node_repo)
    gap_detector = LearningGapDetector(gap_repo=gap_repo, concept_repo=node_repo)
    velocity_svc = LearningVelocityService(session_repo=session_repo, mastery_repo=mastery_repo)
    behavior_svc = LearnerBehaviorService(
        session_repo=session_repo, mastery_repo=mastery_repo, gap_repo=gap_repo,
    )

    return LearningOrchestrator(
        extractor=extractor,
        profile_svc=profile_svc,
        session_svc=session_svc,
        mastery_engine=mastery_engine,
        gap_detector=gap_detector,
        velocity_svc=velocity_svc,
        behavior_svc=behavior_svc,
    )


def get_student_profile_service(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> StudentProfileService:
    return StudentProfileService(StudentProfileRepository(db))


def get_session_memory_service(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SessionMemoryService:
    return SessionMemoryService(LearningSessionRepository(db))


def get_mastery_engine(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MasteryEngine:
    return MasteryEngine(
        mastery_repo=MasteryRepository(db),
        concept_repo=ConceptNodeRepository(db),
    )


def get_knowledge_graph_service(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> KnowledgeGraphService:
    return KnowledgeGraphService(
        node_repo=ConceptNodeRepository(db),
        edge_repo=ConceptEdgeRepository(db),
    )


def get_learning_gap_detector(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> LearningGapDetector:
    return LearningGapDetector(
        gap_repo=LearningGapRepository(db),
        concept_repo=ConceptNodeRepository(db),
    )


def get_next_best_topic_engine(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> NextBestTopicEngine:
    return NextBestTopicEngine(
        graph=KnowledgeGraphService(
            node_repo=ConceptNodeRepository(db),
            edge_repo=ConceptEdgeRepository(db),
        ),
        mastery_repo=MasteryRepository(db),
        profile_repo=StudentProfileRepository(db),
    )


def get_learning_velocity_service(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> LearningVelocityService:
    return LearningVelocityService(
        session_repo=LearningSessionRepository(db),
        mastery_repo=MasteryRepository(db),
    )


def get_learning_analytics_service(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> LearningAnalyticsService:
    session_repo = LearningSessionRepository(db)
    mastery_repo = MasteryRepository(db)
    return LearningAnalyticsService(
        session_repo=session_repo,
        mastery_repo=mastery_repo,
        gap_repo=LearningGapRepository(db),
        velocity_svc=LearningVelocityService(session_repo=session_repo, mastery_repo=mastery_repo),
    )
