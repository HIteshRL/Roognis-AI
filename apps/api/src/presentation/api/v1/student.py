from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, status

from src.application.dtos.learning import (
    LearningAnalyticsResponse,
    MasteryRecordResponse,
    RecommendationResponse,
    SessionListResponse,
    StudentProfileResponse,
    UpdateProfileRequest,
)
from src.application.dtos.user import UserResponse
from src.application.interfaces.dependencies import (
    get_current_user,
    get_learning_analytics_service,
    get_learning_gap_detector,
    get_mastery_engine,
    get_next_best_topic_engine,
    get_session_memory_service,
    get_student_profile_service,
)
from src.application.services.learning_analytics_service import LearningAnalyticsService
from src.application.services.learning_gap_detector import LearningGapDetector
from src.application.services.mastery_engine import MasteryEngine
from src.application.services.next_best_topic_engine import NextBestTopicEngine
from src.application.services.session_memory_service import SessionMemoryService
from src.application.services.student_profile_service import StudentProfileService
from src.presentation.api.response import ok, paginated

router = APIRouter(prefix="/student", tags=["Learning Engine"])


@router.get("/profile", response_model=None)
async def get_profile(
    request: Request,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    profile_svc: Annotated[StudentProfileService, Depends(get_student_profile_service)],
):
    profile = await profile_svc.get_or_create(UUID(current_user.id))
    return ok(
        StudentProfileResponse(
            id=profile.id,
            user_id=profile.user_id,
            institution=profile.institution,
            grade=profile.grade,
            subjects=profile.subjects,
            current_chapter=profile.current_chapter,
            learning_velocity=profile.learning_velocity,
            confidence_score=profile.confidence_score,
            last_active=profile.last_active,
            created_at=profile.created_at,
            updated_at=profile.updated_at,
        ).model_dump(),
        request_id=request.state.request_id,
    )


@router.post("/profile", response_model=None)
async def update_profile(
    body: UpdateProfileRequest,
    request: Request,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    profile_svc: Annotated[StudentProfileService, Depends(get_student_profile_service)],
):
    profile = await profile_svc.update(
        user_id=UUID(current_user.id),
        institution=body.institution,
        grade=body.grade,
        subjects=body.subjects or None,
        current_chapter=body.current_chapter,
    )
    return ok(
        StudentProfileResponse(
            id=profile.id,
            user_id=profile.user_id,
            institution=profile.institution,
            grade=profile.grade,
            subjects=profile.subjects,
            current_chapter=profile.current_chapter,
            learning_velocity=profile.learning_velocity,
            confidence_score=profile.confidence_score,
            last_active=profile.last_active,
            created_at=profile.created_at,
            updated_at=profile.updated_at,
        ).model_dump(),
        request_id=request.state.request_id,
    )


@router.get("/sessions", response_model=None)
async def list_sessions(
    request: Request,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    session_svc: Annotated[SessionMemoryService, Depends(get_session_memory_service)],
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
):
    offset = (page - 1) * limit
    sessions, total = await session_svc.list_sessions(
        UUID(current_user.id), limit=limit, offset=offset
    )
    return paginated(
        data=[
            {
                "id": str(s.id),
                "user_id": str(s.user_id),
                "conversation_id": str(s.conversation_id) if s.conversation_id else None,
                "subject": s.subject,
                "chapter": s.chapter,
                "grade": s.grade,
                "question": s.question,
                "primary_concept": s.primary_concept,
                "concepts_discussed": s.concepts_discussed,
                "bloom_level": s.bloom_level,
                "difficulty_level": s.difficulty_level,
                "misconceptions": s.misconceptions,
                "token_count": s.token_count,
                "duration_ms": s.duration_ms,
                "created_at": s.created_at.isoformat(),
            }
            for s in sessions
        ],
        total=total,
        page=page,
        limit=limit,
        request_id=request.state.request_id,
    )


@router.get("/mastery", response_model=None)
async def get_mastery(
    request: Request,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    mastery_engine: Annotated[MasteryEngine, Depends(get_mastery_engine)],
):
    records = await mastery_engine.get_all(UUID(current_user.id))
    return ok(
        [
            MasteryRecordResponse(
                id=r.id,
                concept_id=r.concept_id,
                concept_name=r.concept_name,
                score=r.score,
                label=r.label,
                interaction_count=r.interaction_count,
                last_updated=r.last_updated,
            ).model_dump()
            for r in records
        ],
        request_id=request.state.request_id,
    )


@router.get("/gaps", response_model=None)
async def get_gaps(
    request: Request,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    gap_detector: Annotated[LearningGapDetector, Depends(get_learning_gap_detector)],
    include_resolved: bool = Query(default=False),
):
    gaps = await gap_detector.list_gaps(
        UUID(current_user.id), include_resolved=include_resolved
    )
    return ok(
        [
            {
                "id": str(g.id),
                "concept_id": str(g.concept_id),
                "concept_name": g.concept_name,
                "severity": g.severity,
                "reason": g.reason,
                "confidence": g.confidence,
                "occurrence_count": g.occurrence_count,
                "is_resolved": g.is_resolved,
                "created_at": g.created_at.isoformat(),
                "updated_at": g.updated_at.isoformat(),
            }
            for g in gaps
        ],
        request_id=request.state.request_id,
    )


@router.post("/gaps/{gap_id}/resolve", response_model=None)
async def resolve_gap(
    gap_id: UUID,
    request: Request,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    gap_detector: Annotated[LearningGapDetector, Depends(get_learning_gap_detector)],
):
    await gap_detector.resolve(gap_id)
    return ok({"resolved": True}, request_id=request.state.request_id)


@router.get("/recommendations", response_model=None)
async def get_recommendations(
    request: Request,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    engine: Annotated[NextBestTopicEngine, Depends(get_next_best_topic_engine)],
):
    recs = await engine.recommend(UUID(current_user.id))
    return ok(
        [
            RecommendationResponse(
                concept_id=r.concept_id,
                concept_name=r.concept_name,
                subject=r.subject,
                chapter=r.chapter,
                reason=r.reason,
                readiness_score=r.readiness_score,
            ).model_dump()
            for r in recs
        ],
        request_id=request.state.request_id,
    )


@router.get("/analytics", response_model=None)
async def get_analytics(
    request: Request,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    analytics_svc: Annotated[LearningAnalyticsService, Depends(get_learning_analytics_service)],
):
    analytics = await analytics_svc.get_analytics(UUID(current_user.id))
    return ok(
        {
            "user_id": str(analytics.user_id),
            "total_sessions": analytics.total_sessions,
            "total_concepts_encountered": analytics.total_concepts_encountered,
            "average_mastery": analytics.average_mastery,
            "mastered_count": analytics.mastered_count,
            "developing_count": analytics.developing_count,
            "emerging_count": analytics.emerging_count,
            "not_started_count": analytics.not_started_count,
            "active_gaps": analytics.active_gaps,
            "critical_gaps": analytics.critical_gaps,
            "recent_bloom_levels": analytics.recent_bloom_levels,
            "recent_concepts": analytics.recent_concepts,
        },
        request_id=request.state.request_id,
    )
