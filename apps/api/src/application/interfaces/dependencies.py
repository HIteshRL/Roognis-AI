"""
FastAPI dependency providers — single source of truth for service construction.
All services are assembled here. Routes receive fully-constructed services.
"""
from contextlib import asynccontextmanager
from typing import Annotated

import structlog
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.application.dtos.user import UserResponse
from src.application.services.attachment_service import AttachmentService
from src.application.services.auth_service import AuthService
from src.application.services.caching_engine import CachingEngine
from src.application.services.chat_service import ChatService
from src.application.services.classroom_analytics_service import ClassroomAnalyticsService
from src.application.services.classroom_service import ClassroomService
from src.application.services.concept_extraction_service import ConceptExtractionService
from src.application.services.concept_memory_service import ConceptMemoryService
from src.application.services.context_validation_service import ContextValidationService
from src.application.services.document_service import DocumentService
from src.application.services.faq_service import FaqService
from src.application.services.intent_engine import IntentEngine
from src.application.services.knowledge_graph_service import KnowledgeGraphService
from src.application.services.knowledge_library_service import KnowledgeLibraryService
from src.application.services.learner_behavior_service import LearnerBehaviorService
from src.application.services.learner_context_service import LearnerContextService
from src.application.services.learning_analytics_service import LearningAnalyticsService
from src.application.services.learning_gap_detector import LearningGapDetector
from src.application.services.learning_orchestrator import LearningOrchestrator
from src.application.services.learning_path_service import LearningPathService
from src.application.services.learning_velocity_service import LearningVelocityService
from src.application.services.mastery_engine import MasteryEngine
from src.application.services.next_best_topic_engine import NextBestTopicEngine
from src.application.services.parent_service import ParentService
from src.application.services.prompt_assembly_service import PromptAssemblyService
from src.application.services.psychometric_assessment_service import (
    PsychometricAssessmentService,
)
from src.application.services.quiz_generation_service import QuizGenerationService
from src.application.services.quiz_service import QuizService
from src.application.services.rag_service import RagService
from src.application.services.response_image_service import ResponseImageService
from src.application.services.retrieval_service import RetrievalService
from src.application.services.school_service import SchoolService
from src.application.services.search_service import SearchService
from src.application.services.session_memory_service import SessionMemoryService
from src.application.services.skill_graph_service import SkillGraphService
from src.application.services.student_profile_service import StudentProfileService
from src.application.services.syllabus_service import SyllabusService
from src.application.services.user_service import UserService
from src.application.services.vector_service import VectorService
from src.application.services.video_generation_service import VideoGenerationService
from src.config import Settings, get_settings
from src.domain.exceptions import AuthenticationError
from src.infrastructure.cache.redis_client import get_redis
from src.infrastructure.database.repositories.attachment_repository import (
    MessageAttachmentRepository,
)
from src.infrastructure.database.repositories.conversation_repository import (
    ConversationRepository,
    MessageRepository,
)
from src.infrastructure.database.repositories.faq_repository import FaqRepository
from src.infrastructure.database.repositories.guardian_repository import (
    GuardianRepository,
)
from src.infrastructure.database.repositories.knowledge_repository import (
    ChunkRepository,
    DocumentRepository,
    IngestionJobRepository,
    KnowledgeBaseRepository,
)
from src.infrastructure.database.repositories.learning_repository import (
    ConceptEdgeRepository,
    ConceptMemoryRepository,
    ConceptNodeRepository,
    LearningGapRepository,
    LearningSessionRepository,
    MasteryRepository,
    StudentProfileRepository,
)
from src.infrastructure.database.repositories.media_job_repository import (
    MediaJobRepository,
)
from src.infrastructure.database.repositories.profile_repository import (
    ProfileRepository,
    SettingsRepository,
)
from src.infrastructure.database.repositories.psychometric_repository import (
    PsychometricRepository,
)
from src.infrastructure.database.repositories.quiz_repository import (
    QuizAttemptRepository,
    QuizQuestionRepository,
    QuizRepository,
    QuizResponseRepository,
)
from src.infrastructure.database.repositories.school_repository import (
    ClassroomRepository,
    EnrollmentRepository,
    SchoolMemberRepository,
    SchoolRepository,
    SyllabusRepository,
)
from src.infrastructure.database.repositories.user_repository import UserRepository
from src.infrastructure.database.session import AsyncSession, AsyncSessionLocal, get_db
from src.infrastructure.embeddings.factory import get_embedding_provider
from src.infrastructure.imagegen.factory import get_image_generator
from src.infrastructure.llm.factory import get_llm_provider
from src.infrastructure.llm.prompt_loader import PromptLoader
from src.infrastructure.storage.local_storage import LocalFileStorage
from src.infrastructure.vector.factory import get_vector_store
from src.infrastructure.videogen.factory import get_video_generator

logger = structlog.get_logger(__name__)
_bearer = HTTPBearer(auto_error=False)


@asynccontextmanager
async def _faq_writer():
    """Fresh, isolated session for FAQ promotion writes (see CachingEngine)."""
    async with AsyncSessionLocal() as session:
        yield FaqRepository(session)
        await session.commit()


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


async def require_teacher(
    current_user: Annotated[UserResponse, Depends(get_current_user)],
) -> UserResponse:
    role = getattr(current_user, "role", "student")
    if role not in ("teacher", "school_admin") and not getattr(
        current_user, "is_admin", False
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message": "Teacher access required"},
        )
    return current_user


# ── User / Chat ───────────────────────────────────────────────────────────────

def get_user_service(db: Annotated[AsyncSession, Depends(get_db)]) -> UserService:
    return UserService(
        profile_repo=ProfileRepository(db),
        settings_repo=SettingsRepository(db),
    )


def get_attachment_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AttachmentService:
    return AttachmentService(
        attachment_repo=MessageAttachmentRepository(db),
        storage=LocalFileStorage(settings.storage_local_path),
        allowed_image_types=settings.allowed_image_types,
        max_image_size_bytes=settings.max_image_size_bytes,
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
            rerank_enabled=settings.retrieval_rerank_enabled,
            rerank_pool=settings.retrieval_rerank_pool,
            lexical_weight=settings.retrieval_lexical_weight,
        )
        prompt_assembly_svc = PromptAssemblyService(prompt_loader)
        context_validation_svc = ContextValidationService(settings.retrieval_score_threshold)
    else:
        retrieval_svc = None
        prompt_assembly_svc = None
        context_validation_svc = None

    concept_memory_svc = ConceptMemoryService(
        memory_repo=ConceptMemoryRepository(db),
        concept_repo=ConceptNodeRepository(db),
    )
    psychometric_svc = PsychometricAssessmentService(
        psychometric_repo=PsychometricRepository(db),
        profile_repo=StudentProfileRepository(db),
    )
    learner_context_svc = LearnerContextService(
        profile_repo=StudentProfileRepository(db),
        mastery_repo=MasteryRepository(db),
        gap_repo=LearningGapRepository(db),
        concept_memory_svc=concept_memory_svc,
        psychometric_svc=psychometric_svc,
    )

    attachment_repo = MessageAttachmentRepository(db)
    attachment_svc = AttachmentService(
        attachment_repo=attachment_repo,
        storage=LocalFileStorage(settings.storage_local_path),
        allowed_image_types=settings.allowed_image_types,
        max_image_size_bytes=settings.max_image_size_bytes,
    )

    response_image_svc = None
    if settings.image_gen_enabled:
        response_image_svc = ResponseImageService(
            image_generator=get_image_generator(),
            attachment_svc=attachment_svc,
            attachment_repo=attachment_repo,
            image_size=settings.image_gen_size,
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
        profile_repo=StudentProfileRepository(db),
        attachment_repo=attachment_repo,
        attachment_svc=attachment_svc,
        vision_model=settings.groq_vision_model,
        vision_enabled=settings.vision_enabled,
        response_image_svc=response_image_svc,
        response_image_enabled=settings.response_image_enabled,
    )


def get_video_generation_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> VideoGenerationService:
    return VideoGenerationService(
        video_generator=get_video_generator(),
        job_repo=MediaJobRepository(db),
        message_repo=MessageRepository(db),
        conversation_repo=ConversationRepository(db),
        storage_path=settings.storage_local_path,
        num_frames=settings.video_num_frames,
        fps=settings.video_fps,
        max_concurrent=settings.max_concurrent_video_jobs,
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
        rerank_enabled=settings.retrieval_rerank_enabled,
        rerank_pool=settings.retrieval_rerank_pool,
        lexical_weight=settings.retrieval_lexical_weight,
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
        rerank_enabled=settings.retrieval_rerank_enabled,
        rerank_pool=settings.retrieval_rerank_pool,
        lexical_weight=settings.retrieval_lexical_weight,
    )
    prompt_loader = PromptLoader(db)
    prompt_assembly_svc = PromptAssemblyService(prompt_loader)
    context_validation_svc = ContextValidationService(settings.retrieval_score_threshold)

    caching_engine: CachingEngine | None = None
    try:
        redis = await get_redis()
        caching_engine = CachingEngine(
            redis=redis,
            faq_repo=FaqRepository(db),
            faq_writer=_faq_writer,
            default_ttl=settings.cache_default_ttl_seconds,
            hot_ttl=settings.cache_hot_ttl_seconds,
            hot_threshold=settings.cache_hot_threshold,
            faq_promote_threshold=settings.faq_promote_threshold,
        )
    except Exception as exc:
        logger.warning("caching_engine_unavailable", error=str(exc))

    return RagService(
        retrieval_svc=retrieval_svc,
        prompt_assembly_svc=prompt_assembly_svc,
        context_validation_svc=context_validation_svc,
        llm_provider=get_llm_provider(),
        response_cache_svc=caching_engine,
    )


# ── Learning Engine ───────────────────────────────────────────────────────────

def get_learning_orchestrator(
    db: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> LearningOrchestrator:
    from groq import AsyncGroq

    node_repo = ConceptNodeRepository(db)
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
    concept_memory_svc = ConceptMemoryService(
        memory_repo=ConceptMemoryRepository(db),
        concept_repo=node_repo,
    )

    return LearningOrchestrator(
        extractor=extractor,
        profile_svc=profile_svc,
        session_svc=session_svc,
        mastery_engine=mastery_engine,
        gap_detector=gap_detector,
        velocity_svc=velocity_svc,
        behavior_svc=behavior_svc,
        concept_memory_svc=concept_memory_svc,
    )


def get_student_profile_service(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> StudentProfileService:
    return StudentProfileService(StudentProfileRepository(db))


def get_psychometric_service(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PsychometricAssessmentService:
    return PsychometricAssessmentService(
        psychometric_repo=PsychometricRepository(db),
        profile_repo=StudentProfileRepository(db),
    )


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


def get_intent_engine() -> IntentEngine:
    return IntentEngine()


def get_concept_memory_service(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ConceptMemoryService:
    return ConceptMemoryService(
        memory_repo=ConceptMemoryRepository(db),
        concept_repo=ConceptNodeRepository(db),
    )


def get_learning_path_service(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> LearningPathService:
    return LearningPathService(
        graph=KnowledgeGraphService(
            node_repo=ConceptNodeRepository(db),
            edge_repo=ConceptEdgeRepository(db),
        ),
        mastery_repo=MasteryRepository(db),
        profile_repo=StudentProfileRepository(db),
    )


def get_skill_graph_service() -> SkillGraphService:
    return SkillGraphService()


# ── Quiz & Assessment ────────────────────────────────────────────────────────


def get_quiz_generation_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> QuizGenerationService:
    from groq import AsyncGroq

    return QuizGenerationService(
        groq_client=AsyncGroq(api_key=settings.groq_api_key),
        mastery_repo=MasteryRepository(db),
        concept_repo=ConceptNodeRepository(db),
    )


def get_quiz_service(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> QuizService:
    return QuizService(
        quiz_repo=QuizRepository(db),
        question_repo=QuizQuestionRepository(db),
        attempt_repo=QuizAttemptRepository(db),
        response_repo=QuizResponseRepository(db),
        mastery_repo=MasteryRepository(db),
        concept_repo=ConceptNodeRepository(db),
    )


# ── School / Classroom (Phase 0.8) ───────────────────────────────────────────


def get_school_service(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SchoolService:
    return SchoolService(
        school_repo=SchoolRepository(db),
        member_repo=SchoolMemberRepository(db),
        user_repo=UserRepository(db),
    )


def get_classroom_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> ClassroomService:
    return ClassroomService(
        classroom_repo=ClassroomRepository(db),
        enrollment_repo=EnrollmentRepository(db),
        member_repo=SchoolMemberRepository(db),
        syllabus_repo=SyllabusRepository(db),
        user_repo=UserRepository(db),
        join_code_length=settings.classroom_join_code_length,
    )


def get_syllabus_service(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SyllabusService:
    return SyllabusService(
        syllabus_repo=SyllabusRepository(db),
        classroom_repo=ClassroomRepository(db),
        member_repo=SchoolMemberRepository(db),
        enrollment_repo=EnrollmentRepository(db),
    )


def get_classroom_analytics_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    classroom_service: Annotated[ClassroomService, Depends(get_classroom_service)],
) -> ClassroomAnalyticsService:
    return ClassroomAnalyticsService(
        classroom_service=classroom_service,
        mastery_repo=MasteryRepository(db),
        gap_repo=LearningGapRepository(db),
        session_repo=LearningSessionRepository(db),
    )


# ── Cache & FAQ Intelligence (ADR-012) ───────────────────────────────────────


async def get_caching_engine(
    db: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> CachingEngine:
    redis = None
    try:
        redis = await get_redis()
    except Exception as exc:
        logger.warning("caching_engine_redis_unavailable", error=str(exc))
    return CachingEngine(
        redis=redis,
        faq_repo=FaqRepository(db),
        faq_writer=_faq_writer,
        default_ttl=settings.cache_default_ttl_seconds,
        hot_ttl=settings.cache_hot_ttl_seconds,
        hot_threshold=settings.cache_hot_threshold,
        faq_promote_threshold=settings.faq_promote_threshold,
    )


def get_faq_service(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> FaqService:
    return FaqService(faq_repo=FaqRepository(db))


# ── Parent Portal (ADR-013) ──────────────────────────────────────────────────


async def get_parent_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> ParentService:
    redis = None
    try:
        redis = await get_redis()
    except Exception as exc:
        logger.warning("parent_service_redis_unavailable", error=str(exc))

    return ParentService(
        guardian_repo=GuardianRepository(db),
        user_repo=UserRepository(db),
        profile_repo=StudentProfileRepository(db),
        mastery_repo=MasteryRepository(db),
        gap_repo=LearningGapRepository(db),
        session_repo=LearningSessionRepository(db),
        redis=redis,
        code_ttl=settings.parent_link_code_ttl_seconds,
    )
