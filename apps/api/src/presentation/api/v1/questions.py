"""Learner Intelligence — QuestionEngine, evidence, preferences, recall, context."""
import hmac
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status

from src.application.dtos.question import (
    AnswerEvaluationResponse,
    BridgeEvidenceRequest,
    EvidenceResponse,
    GeneratedQuestionResponse,
    LearnerContextResponse,
    LearnerPreferenceResponse,
    QuestionHistoryItem,
    RecallScheduleResponse,
    SubmissionResponse,
    SubmitAnswerRequest,
)
from src.application.dtos.user import UserResponse
from src.application.interfaces.dependencies import (
    get_confidence_updater,
    get_current_user,
    get_evidence_collector,
    get_learner_intelligence_engine,
    get_preference_inference_engine,
    get_questioning_engine,
    get_recall_scheduler,
)
from src.application.services.confidence_updater import ConfidenceUpdater
from src.application.services.evidence_collector import EvidenceCollector
from src.application.services.learner_intelligence_engine import LearnerIntelligenceEngine
from src.application.services.preference_inference_engine import PreferenceInferenceEngine
from src.application.services.questioning_engine import QuestioningEngine, QuestionOwnershipError
from src.application.services.recall_scheduler import RecallScheduler
from src.config import Settings, get_settings
from src.domain.entities.user import User
from src.infrastructure.database.repositories.learning_repository import ConceptNodeRepository
from src.infrastructure.database.repositories.user_repository import UserRepository
from src.infrastructure.database.session import AsyncSession, get_db
from src.presentation.api.response import ok

router = APIRouter(prefix="/learner", tags=["Learner Intelligence"])


@router.get("/questions/next", response_model=None)
async def get_next_question(
    request: Request,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    engine: Annotated[QuestioningEngine, Depends(get_questioning_engine)],
):
    question = await engine.next_question(UUID(current_user.id))
    if question is None:
        return ok(None, message="No question needed — learner state is certain enough.",
                  request_id=request.state.request_id)
    return ok(
        GeneratedQuestionResponse(
            id=question.id,
            concept_id=question.concept_id,
            concept=question.concept_name,
            question=question.question_text,
            purpose=question.purpose,
            objective=question.objective,
            difficulty=question.difficulty,
            bloom_level=question.bloom_level,
            confidence_threshold=question.confidence_threshold,
            evidence_weight=question.evidence_weight,
            status=question.status,
            created_at=question.created_at,
        ).model_dump(mode="json"),
        request_id=request.state.request_id,
    )


@router.post("/questions/{question_id}/answer", response_model=None)
async def submit_answer(
    question_id: UUID,
    body: SubmitAnswerRequest,
    request: Request,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    engine: Annotated[QuestioningEngine, Depends(get_questioning_engine)],
):
    try:
        result = await engine.submit_answer(UUID(current_user.id), question_id, body.answer)
    except QuestionOwnershipError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "QUESTION_NOT_FOUND", "message": str(exc)},
        ) from exc

    ev = result.evaluation
    return ok(
        SubmissionResponse(
            question_id=result.question.id,
            concept=result.question.concept_name,
            evaluation=AnswerEvaluationResponse(
                is_correct=ev.is_correct,
                score=ev.score,
                signal=ev.signal,
                feedback=ev.feedback,
                matched=ev.matched,
                missed=ev.missed,
            ),
            confidence_after=result.confidence_after,
        ).model_dump(mode="json"),
        request_id=request.state.request_id,
    )


@router.get("/questions", response_model=None)
async def list_questions(
    request: Request,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    engine: Annotated[QuestioningEngine, Depends(get_questioning_engine)],
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    limit: int = Query(default=20, ge=1, le=100),
):
    questions = await engine.history(UUID(current_user.id), status=status_filter, limit=limit)
    return ok(
        [
            QuestionHistoryItem(
                id=q.id,
                concept=q.concept_name,
                question=q.question_text,
                objective=q.objective,
                status=q.status,
                is_correct=q.is_correct,
                score=q.score,
                created_at=q.created_at,
            ).model_dump(mode="json")
            for q in questions
        ],
        request_id=request.state.request_id,
    )


@router.get("/recall", response_model=None)
async def get_recall_schedules(
    request: Request,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    scheduler: Annotated[RecallScheduler, Depends(get_recall_scheduler)],
):
    schedules = await scheduler.all(UUID(current_user.id))
    return ok(
        [
            RecallScheduleResponse(
                concept_id=s.concept_id,
                concept_name=s.concept_name,
                interval_days=s.interval_days,
                ease_factor=s.ease_factor,
                repetitions=s.repetitions,
                lapses=s.lapses,
                retention_probability=s.retention_at(),
                next_review_at=s.next_review_at,
                is_due=s.is_due(),
            ).model_dump(mode="json")
            for s in schedules
        ],
        request_id=request.state.request_id,
    )


@router.get("/preferences", response_model=None)
async def get_preferences(
    request: Request,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    engine: Annotated[PreferenceInferenceEngine, Depends(get_preference_inference_engine)],
):
    prefs = await engine.get_preferences(UUID(current_user.id))
    return ok(
        [
            LearnerPreferenceResponse(
                dimension=p.dimension,
                strength=p.strength,
                confidence=p.confidence,
                evidence_count=p.evidence_count,
                is_reliable=p.is_reliable,
                last_updated=p.last_updated,
            ).model_dump(mode="json")
            for p in prefs
        ],
        request_id=request.state.request_id,
    )


@router.get("/evidence", response_model=None)
async def get_evidence(
    request: Request,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    collector: Annotated[EvidenceCollector, Depends(get_evidence_collector)],
    limit: int = Query(default=50, ge=1, le=200),
):
    events = await collector.recent(UUID(current_user.id), limit=limit)
    return ok(
        [
            EvidenceResponse(
                id=e.id,
                concept_name=e.concept_name,
                signal=e.signal,
                objective=e.objective,
                source=e.source,
                weight=e.weight,
                confidence_before=e.confidence_before,
                confidence_after=e.confidence_after,
                confidence_delta=e.confidence_delta,
                detail=e.detail,
                created_at=e.created_at,
            ).model_dump(mode="json")
            for e in events
        ],
        request_id=request.state.request_id,
    )


@router.get("/context", response_model=None)
async def get_learner_context(
    request: Request,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    engine: Annotated[LearnerIntelligenceEngine, Depends(get_learner_intelligence_engine)],
):
    ctx = await engine.build_context(UUID(current_user.id))
    return ok(
        LearnerContextResponse(
            user_id=ctx.user_id,
            weak_concepts=ctx.weak_concepts,
            persistent_gaps=ctx.persistent_gaps,
            preferences=ctx.preferences,
            current_goal=ctx.current_goal,
            memory_state=ctx.memory_state,
            recommendations=ctx.recommendations,
        ).model_dump(mode="json"),
        request_id=request.state.request_id,
    )


# ── Bridge: ingest evidence from an external surface (default OFF) ─────────────

@router.post("/evidence/ingest", response_model=None)
async def ingest_evidence(
    body: BridgeEvidenceRequest,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    confidence_updater: Annotated[ConfidenceUpdater, Depends(get_confidence_updater)],
    x_bridge_token: Annotated[str | None, Header()] = None,
):
    """Service-token authenticated. Maps an external learner ref to a namespaced
    bridge user and drives the real ConfidenceUpdater (mastery + gap + recall +
    evidence). Disabled unless BRIDGE_INGEST_TOKEN is configured."""
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

    # Namespaced bridge user (unusable password → cannot log in via credentials).
    user_repo = UserRepository(db)
    email = f"bridge+{body.external_ref}@bridge.local"
    user = await user_repo.get_by_email(email)
    if user is None:
        user = await user_repo.create(User(
            email=email,
            username=f"bridge_{body.external_ref}"[:50],
            password_hash="!bridge-no-login",
            role="student",
        ))

    node = await ConceptNodeRepository(db).get_or_create(body.concept_name, None, None, None)

    evidence = await confidence_updater.apply_signal(
        user_id=user.id,
        concept_id=node.id,
        concept_name=node.name,
        signal=body.signal,
        objective=body.objective,
        source=body.source,
        weight=body.weight,
        bloom_level=body.bloom_level,
        intent=body.intent,
        detail=body.detail,
    )
    return ok(
        {
            "user_id": str(user.id),
            "concept_id": str(node.id),
            "signal": evidence.signal,
            "confidence_after": evidence.confidence_after,
        },
        request_id=request.state.request_id,
    )
