from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request

from src.application.dtos.quiz import (
    GenerateQuizRequest,
    QuestionResultResponse,
    QuizAttemptResponse,
    QuizDetailResponse,
    QuizQuestionResponse,
    QuizResultResponse,
    QuizSummaryResponse,
    SubmitQuizRequest,
)
from src.application.dtos.user import UserResponse
from src.application.interfaces.dependencies import (
    get_current_user,
    get_learning_velocity_service,
    get_quiz_generation_service,
    get_quiz_service,
)
from src.application.services.learning_velocity_service import (
    LearningVelocityService,
)
from src.application.services.quiz_generation_service import (
    QuizGenerationService,
)
from src.application.services.quiz_service import QuizService
from src.presentation.api.response import ok, paginated

router = APIRouter(prefix="/student/quiz", tags=["Quiz & Assessment"])


def _quiz_summary(q) -> dict:
    return QuizSummaryResponse(
        id=q.id,
        title=q.title,
        subject=q.subject,
        chapter=q.chapter,
        difficulty=q.difficulty,
        question_count=q.question_count,
        total_attempts=q.total_attempts,
        best_score=q.best_score,
        created_at=q.created_at,
    ).model_dump(mode="json")


def _attempt_response(a) -> dict:
    return QuizAttemptResponse(
        id=a.id,
        quiz_id=a.quiz_id,
        score=a.score,
        correct_count=a.correct_count,
        total_answered=a.total_answered,
        total_time_ms=a.total_time_ms,
        started_at=a.started_at,
        completed_at=a.completed_at,
    ).model_dump(mode="json")


@router.post("/generate", response_model=None)
async def generate_quiz(
    body: GenerateQuizRequest,
    request: Request,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    gen_svc: Annotated[
        QuizGenerationService, Depends(get_quiz_generation_service)
    ],
    quiz_svc: Annotated[QuizService, Depends(get_quiz_service)],
):
    concept_ids = (
        [UUID(cid) for cid in body.concept_ids]
        if body.concept_ids
        else None
    )
    quiz, questions = await gen_svc.generate(
        user_id=UUID(current_user.id),
        subject=body.subject,
        chapter=body.chapter,
        concept_ids=concept_ids,
        question_count=body.question_count,
        difficulty=body.difficulty,
    )

    if not questions:
        return ok(
            {"message": "No concepts found to generate questions from"},
            request_id=request.state.request_id,
        )

    saved_quiz = await quiz_svc.create_quiz(quiz, questions)
    return ok(_quiz_summary(saved_quiz), request_id=request.state.request_id)


@router.get("", response_model=None)
async def list_quizzes(
    request: Request,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    quiz_svc: Annotated[QuizService, Depends(get_quiz_service)],
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    subject: str | None = Query(default=None),
):
    offset = (page - 1) * limit
    quizzes, total = await quiz_svc.list_quizzes(
        UUID(current_user.id), subject, limit, offset
    )
    return paginated(
        data=[_quiz_summary(q) for q in quizzes],
        total=total,
        page=page,
        limit=limit,
        request_id=request.state.request_id,
    )


@router.get("/history", response_model=None)
async def quiz_history(
    request: Request,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    quiz_svc: Annotated[QuizService, Depends(get_quiz_service)],
    limit: int = Query(default=10, ge=1, le=50),
):
    history = await quiz_svc.quiz_history(UUID(current_user.id), limit)
    return ok(
        [
            {
                "attempt": _attempt_response(h["attempt"]),
                "quiz_title": h["quiz_title"],
                "quiz_subject": h["quiz_subject"],
            }
            for h in history
        ],
        request_id=request.state.request_id,
    )


@router.post("/review", response_model=None)
async def review_quiz(
    request: Request,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    velocity_svc: Annotated[
        LearningVelocityService, Depends(get_learning_velocity_service)
    ],
    gen_svc: Annotated[QuizGenerationService, Depends(get_quiz_generation_service)],
    quiz_svc: Annotated[QuizService, Depends(get_quiz_service)],
    question_count: int = Query(default=5, ge=1, le=20),
):
    """Spaced-repetition entry point: build a quiz from the concepts most at
    risk of being forgotten (retention risk), targeting the student's ability."""
    user_id = UUID(current_user.id)
    risks = await velocity_svc.compute_retention_risks(user_id)
    if not risks:
        return ok(
            None,
            message="Nothing is due for review — keep learning!",
            request_id=request.state.request_id,
        )

    concept_ids = [r.concept_id for r in risks[:question_count]]
    quiz, questions = await gen_svc.generate(
        user_id=user_id,
        concept_ids=concept_ids,
        question_count=question_count,
        difficulty="adaptive",
    )
    if not questions:
        return ok(
            None,
            message="Could not build a review quiz right now",
            request_id=request.state.request_id,
        )

    quiz.title = "Review — concepts due for reinforcement"
    saved_quiz = await quiz_svc.create_quiz(quiz, questions)
    return ok(_quiz_summary(saved_quiz), request_id=request.state.request_id)


@router.get("/{quiz_id}", response_model=None)
async def get_quiz(
    quiz_id: UUID,
    request: Request,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    quiz_svc: Annotated[QuizService, Depends(get_quiz_service)],
):
    result = await quiz_svc.get_quiz(quiz_id, UUID(current_user.id))
    if not result:
        return ok(None, request_id=request.state.request_id)

    quiz, questions = result
    return ok(
        QuizDetailResponse(
            id=quiz.id,
            title=quiz.title,
            subject=quiz.subject,
            chapter=quiz.chapter,
            difficulty=quiz.difficulty,
            question_count=quiz.question_count,
            questions=[
                QuizQuestionResponse(
                    id=q.id,
                    concept_name=q.concept_name,
                    question_text=q.question_text,
                    question_type=q.question_type,
                    options=q.options,
                    bloom_level=q.bloom_level,
                    difficulty=q.difficulty,
                    position=q.position,
                )
                for q in questions
            ],
            created_at=quiz.created_at,
        ).model_dump(mode="json"),
        request_id=request.state.request_id,
    )


@router.post("/{quiz_id}/start", response_model=None)
async def start_attempt(
    quiz_id: UUID,
    request: Request,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    quiz_svc: Annotated[QuizService, Depends(get_quiz_service)],
):
    attempt = await quiz_svc.start_attempt(UUID(current_user.id), quiz_id)
    return ok(_attempt_response(attempt), request_id=request.state.request_id)


@router.post("/{quiz_id}/submit", response_model=None)
async def submit_quiz(
    quiz_id: UUID,
    body: SubmitQuizRequest,
    request: Request,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    quiz_svc: Annotated[QuizService, Depends(get_quiz_service)],
):
    attempt = await quiz_svc.start_attempt(UUID(current_user.id), quiz_id)
    completed = await quiz_svc.submit_and_complete(
        user_id=UUID(current_user.id),
        quiz_id=quiz_id,
        attempt_id=attempt.id,
        responses=[r.model_dump() for r in body.responses],
    )
    return ok(_attempt_response(completed), request_id=request.state.request_id)


@router.get("/attempts/{attempt_id}/results", response_model=None)
async def get_attempt_results(
    attempt_id: UUID,
    request: Request,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    quiz_svc: Annotated[QuizService, Depends(get_quiz_service)],
):
    data = await quiz_svc.get_attempt_results(
        attempt_id, UUID(current_user.id)
    )
    if not data:
        return ok(None, request_id=request.state.request_id)

    attempt = data["attempt"]
    quiz = data["quiz"]
    return ok(
        QuizResultResponse(
            attempt=QuizAttemptResponse(
                id=attempt.id,
                quiz_id=attempt.quiz_id,
                score=attempt.score,
                correct_count=attempt.correct_count,
                total_answered=attempt.total_answered,
                total_time_ms=attempt.total_time_ms,
                started_at=attempt.started_at,
                completed_at=attempt.completed_at,
            ),
            quiz_title=quiz.title,
            quiz_subject=quiz.subject,
            results=[
                QuestionResultResponse(
                    question_id=r["question_id"],
                    question_text=r["question_text"],
                    options=r["options"],
                    selected_answer=r["selected_answer"],
                    correct_answer=r["correct_answer"],
                    is_correct=r["is_correct"],
                    explanation=r["explanation"],
                    concept_name=r["concept_name"],
                )
                for r in data["results"]
            ],
        ).model_dump(mode="json"),
        request_id=request.state.request_id,
    )
