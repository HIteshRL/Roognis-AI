"""
FastAPI dependency providers — single source of truth for service construction.
All services are assembled here. Routes receive fully-constructed services.
"""
import hmac
from typing import Annotated

import structlog
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.application.dtos.user import UserResponse
from src.application.services.admin_service import AdminService
from src.application.services.answer_evaluator import AnswerEvaluator
from src.application.services.auth_service import AuthService
from src.application.services.bridge_ingestion_service import BridgeIngestionService
from src.application.services.chat_service import ChatService
from src.application.services.classroom_service import ClassroomService
from src.application.services.concept_extraction_service import ConceptExtractionService
from src.application.services.concept_memory_service import ConceptMemoryService
from src.application.services.confidence_updater import ConfidenceUpdater
from src.application.services.context_validation_service import ContextValidationService
from src.application.services.coursework_service import CourseworkService
from src.application.services.discussion_service import DiscussionService
from src.application.services.document_service import DocumentService
from src.application.services.evidence_collector import EvidenceCollector
from src.application.services.intent_engine import IntentEngine
from src.application.services.knowledge_graph_service import KnowledgeGraphService
from src.application.services.knowledge_library_service import KnowledgeLibraryService
from src.application.services.learner_behavior_service import LearnerBehaviorService
from src.application.services.learner_context_service import LearnerContextService
from src.application.services.learner_intelligence_engine import LearnerIntelligenceEngine
from src.application.services.learning_analytics_service import LearningAnalyticsService
from src.application.services.learning_gap_detector import LearningGapDetector
from src.application.services.learning_orchestrator import LearningOrchestrator
from src.application.services.learning_path_service import LearningPathService
from src.application.services.learning_velocity_service import LearningVelocityService
from src.application.services.mastery_engine import MasteryEngine
from src.application.services.material_service import MaterialService
from src.application.services.next_best_topic_engine import NextBestTopicEngine
from src.application.services.notification_service import NotificationService
from src.application.services.preference_inference_engine import PreferenceInferenceEngine
from src.application.services.prompt_assembly_service import PromptAssemblyService
from src.application.services.question_generator import QuestionGenerator
from src.application.services.question_scheduler import QuestionScheduler
from src.application.services.questioning_engine import QuestioningEngine
from src.application.services.rag_service import RagService
from src.application.services.recall_scheduler import RecallScheduler
from src.application.services.response_cache_service import ResponseCacheService
from src.application.services.retrieval_service import RetrievalService
from src.application.services.search_service import SearchService
from src.application.services.session_memory_service import SessionMemoryService
from src.application.services.skill_graph_service import SkillGraphService
from src.application.services.student_dashboard_service import StudentDashboardService
from src.application.services.student_profile_service import StudentProfileService
from src.application.services.submission_service import SubmissionService
from src.application.services.teacher_analytics_service import TeacherAnalyticsService
from src.application.services.user_service import UserService
from src.application.services.vector_service import VectorService
from src.application.services.vision_ocr_service import VisionOCRService
from src.config import Settings, get_settings
from src.domain.exceptions import AuthenticationError
from src.infrastructure.cache.redis_client import get_redis
from src.infrastructure.database.repositories.classroom_repository import (
    ChapterRepository,
    ClassroomRepository,
    EnrollmentRepository,
)
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
    ConceptMemoryRepository,
    ConceptNodeRepository,
    LearningGapRepository,
    LearningSessionRepository,
    MasteryRepository,
    StudentProfileRepository,
)
from src.infrastructure.database.repositories.lms_repository import (
    AuditLogRepository,
    AuthTokenRepository,
    BookmarkRepository,
    ClassroomTeacherRepository,
    CommentRepository,
    CourseworkRepository,
    FolderRepository,
    InstitutionRepository,
    InvitationRepository,
    LmsAnalyticsRepository,
    MaterialRepository,
    MaterialViewRepository,
    NotificationRepository,
    SessionRepository,
    SubmissionRepository,
)
from src.infrastructure.database.repositories.profile_repository import (
    ProfileRepository,
    SettingsRepository,
)
from src.infrastructure.database.repositories.question_repository import (
    EvidenceRepository,
    LearnerPreferenceRepository,
    LearnerQuestionRepository,
    RecallScheduleRepository,
)
from src.infrastructure.database.repositories.user_repository import UserRepository
from src.infrastructure.database.session import AsyncSession, get_db
from src.infrastructure.email.factory import get_email_provider
from src.infrastructure.embeddings.factory import get_embedding_provider
from src.infrastructure.llm.factory import get_llm_provider
from src.infrastructure.llm.prompt_loader import PromptLoader
from src.infrastructure.storage.factory import get_file_storage
from src.infrastructure.vector.factory import get_vector_store
from src.infrastructure.vision.factory import get_vision_provider

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
        auth_token_repo=AuthTokenRepository(db),
        session_repo=SessionRepository(db),
        email_provider=get_email_provider(),
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
    if getattr(current_user, "role", "student") != "teacher" and not getattr(
        current_user, "is_admin", False
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message": "Teacher access required"},
        )
    return current_user


def require_bridge_token(
    settings: Annotated[Settings, Depends(get_settings)],
    x_bridge_token: Annotated[str | None, Header()] = None,
) -> None:
    """Guards the evidence-ingest bridge with a shared service token.

    Disabled (404) unless BRIDGE_INGEST_TOKEN is configured; 401 on mismatch.
    Kept as a dependency so the route body carries no auth logic.
    """
    token = settings.bridge_ingest_token
    if not token:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "BRIDGE_DISABLED", "message": "Evidence bridge is not enabled"},
        )
    if not x_bridge_token or not hmac.compare_digest(x_bridge_token, token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "BRIDGE_UNAUTHORIZED", "message": "Invalid bridge token"},
        )


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

    concept_memory_svc = ConceptMemoryService(
        memory_repo=ConceptMemoryRepository(db),
        concept_repo=ConceptNodeRepository(db),
    )
    learner_context_svc = LearnerContextService(
        profile_repo=StudentProfileRepository(db),
        mastery_repo=MasteryRepository(db),
        gap_repo=LearningGapRepository(db),
        concept_memory_svc=concept_memory_svc,
        recall_scheduler=RecallScheduler(schedule_repo=RecallScheduleRepository(db)),
        preference_engine=PreferenceInferenceEngine(
            preference_repo=LearnerPreferenceRepository(db)
        ),
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
        storage=get_file_storage(settings),
        vector_svc=vector_svc,
        settings=settings,
    )


def get_vision_ocr_service(settings: Settings | None = None) -> VisionOCRService:
    """Vision OCR enrichment for the ingestion pipeline (Phase 0.6).

    Callable both as a FastAPI dependency and directly from route-level pipeline
    builders, so ``settings`` is optional and resolved from the cache when absent.
    """
    settings = settings or get_settings()
    return VisionOCRService(
        vision_provider=get_vision_provider(),
        enabled=settings.ocr_enabled,
        min_chars_per_page=settings.ocr_min_chars_per_page,
        max_pages=settings.ocr_max_pages,
        max_image_dimension=settings.ocr_max_image_dimension,
        image_format=settings.ocr_image_format,
    )


def get_classroom_service(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ClassroomService:
    return ClassroomService(
        classroom_repo=ClassroomRepository(db),
        chapter_repo=ChapterRepository(db),
        enrollment_repo=EnrollmentRepository(db),
        kb_repo=KnowledgeBaseRepository(db),
        user_repo=UserRepository(db),
        doc_repo=DocumentRepository(db),
        teacher_repo=ClassroomTeacherRepository(db),
        invitation_repo=InvitationRepository(db),
        notification_svc=NotificationService(NotificationRepository(db)),
    )


# ── LMS (Google Classroom parity) ────────────────────────────────────────────

def get_notification_service(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> NotificationService:
    return NotificationService(NotificationRepository(db))


def get_material_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> MaterialService:
    return MaterialService(
        material_repo=MaterialRepository(db),
        folder_repo=FolderRepository(db),
        classroom_repo=ClassroomRepository(db),
        enrollment_repo=EnrollmentRepository(db),
        teacher_repo=ClassroomTeacherRepository(db),
        bookmark_repo=BookmarkRepository(db),
        view_repo=MaterialViewRepository(db),
        storage=get_file_storage(settings),
        notification_svc=NotificationService(NotificationRepository(db)),
    )


def get_coursework_service(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CourseworkService:
    return CourseworkService(
        coursework_repo=CourseworkRepository(db),
        classroom_repo=ClassroomRepository(db),
        enrollment_repo=EnrollmentRepository(db),
        teacher_repo=ClassroomTeacherRepository(db),
        submission_repo=SubmissionRepository(db),
        notification_svc=NotificationService(NotificationRepository(db)),
    )


def get_submission_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> SubmissionService:
    return SubmissionService(
        submission_repo=SubmissionRepository(db),
        coursework_repo=CourseworkRepository(db),
        classroom_repo=ClassroomRepository(db),
        enrollment_repo=EnrollmentRepository(db),
        teacher_repo=ClassroomTeacherRepository(db),
        user_repo=UserRepository(db),
        storage=get_file_storage(settings),
        notification_svc=NotificationService(NotificationRepository(db)),
    )


def get_discussion_service(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DiscussionService:
    return DiscussionService(
        comment_repo=CommentRepository(db),
        classroom_repo=ClassroomRepository(db),
        enrollment_repo=EnrollmentRepository(db),
        teacher_repo=ClassroomTeacherRepository(db),
        user_repo=UserRepository(db),
        notification_svc=NotificationService(NotificationRepository(db)),
    )


def get_teacher_analytics_service(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TeacherAnalyticsService:
    return TeacherAnalyticsService(
        analytics_repo=LmsAnalyticsRepository(db),
        classroom_repo=ClassroomRepository(db),
        enrollment_repo=EnrollmentRepository(db),
        teacher_repo=ClassroomTeacherRepository(db),
    )


def get_student_dashboard_service(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> StudentDashboardService:
    return StudentDashboardService(
        enrollment_repo=EnrollmentRepository(db),
        coursework_repo=CourseworkRepository(db),
        submission_repo=SubmissionRepository(db),
        bookmark_repo=BookmarkRepository(db),
        view_repo=MaterialViewRepository(db),
        material_repo=MaterialRepository(db),
    )


def get_admin_service(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AdminService:
    return AdminService(
        institution_repo=InstitutionRepository(db),
        user_repo=UserRepository(db),
        classroom_repo=ClassroomRepository(db),
        audit_repo=AuditLogRepository(db),
        analytics_repo=LmsAnalyticsRepository(db),
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
    evidence_collector = EvidenceCollector(evidence_repo=EvidenceRepository(db))
    preference_engine = PreferenceInferenceEngine(
        preference_repo=LearnerPreferenceRepository(db)
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
        evidence_collector=evidence_collector,
        preference_engine=preference_engine,
        concept_repo=node_repo,
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


# ── Learner Intelligence: QuestionEngine + Evidence ───────────────────────────

def get_evidence_collector(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> EvidenceCollector:
    return EvidenceCollector(evidence_repo=EvidenceRepository(db))


def get_recall_scheduler(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RecallScheduler:
    return RecallScheduler(schedule_repo=RecallScheduleRepository(db))


def get_preference_inference_engine(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PreferenceInferenceEngine:
    return PreferenceInferenceEngine(preference_repo=LearnerPreferenceRepository(db))


def get_confidence_updater(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ConfidenceUpdater:
    return ConfidenceUpdater(
        evidence_collector=EvidenceCollector(evidence_repo=EvidenceRepository(db)),
        recall_scheduler=RecallScheduler(schedule_repo=RecallScheduleRepository(db)),
        mastery_repo=MasteryRepository(db),
        concept_repo=ConceptNodeRepository(db),
        gap_repo=LearningGapRepository(db),
    )


def get_bridge_ingestion_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    confidence_updater: Annotated[ConfidenceUpdater, Depends(get_confidence_updater)],
) -> BridgeIngestionService:
    return BridgeIngestionService(
        user_repo=UserRepository(db),
        concept_repo=ConceptNodeRepository(db),
        confidence_updater=confidence_updater,
    )


def get_questioning_engine(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> QuestioningEngine:
    evidence_collector = EvidenceCollector(evidence_repo=EvidenceRepository(db))
    recall_scheduler = RecallScheduler(schedule_repo=RecallScheduleRepository(db))
    scheduler = QuestionScheduler(
        mastery_repo=MasteryRepository(db),
        recall_scheduler=recall_scheduler,
        evidence_collector=evidence_collector,
        concept_repo=ConceptNodeRepository(db),
        gap_repo=LearningGapRepository(db),
    )
    confidence_updater = ConfidenceUpdater(
        evidence_collector=evidence_collector,
        recall_scheduler=recall_scheduler,
        mastery_repo=MasteryRepository(db),
        concept_repo=ConceptNodeRepository(db),
        gap_repo=LearningGapRepository(db),
    )
    return QuestioningEngine(
        scheduler=scheduler,
        generator=QuestionGenerator(),
        evaluator=AnswerEvaluator(),
        confidence_updater=confidence_updater,
        question_repo=LearnerQuestionRepository(db),
    )


def get_learner_intelligence_engine(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> LearnerIntelligenceEngine:
    node_repo = ConceptNodeRepository(db)
    return LearnerIntelligenceEngine(
        mastery_repo=MasteryRepository(db),
        gap_repo=LearningGapRepository(db),
        preference_engine=PreferenceInferenceEngine(preference_repo=LearnerPreferenceRepository(db)),
        recall_scheduler=RecallScheduler(schedule_repo=RecallScheduleRepository(db)),
        concept_memory_svc=ConceptMemoryService(
            memory_repo=ConceptMemoryRepository(db),
            concept_repo=node_repo,
        ),
        recommender=NextBestTopicEngine(
            graph=KnowledgeGraphService(
                node_repo=node_repo,
                edge_repo=ConceptEdgeRepository(db),
            ),
            mastery_repo=MasteryRepository(db),
            profile_repo=StudentProfileRepository(db),
        ),
    )
