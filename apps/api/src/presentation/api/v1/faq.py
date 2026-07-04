from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from src.application.dtos.cache import FaqResponse
from src.application.dtos.user import UserResponse
from src.application.interfaces.dependencies import get_current_user, get_faq_service
from src.application.services.faq_service import FaqService
from src.presentation.api.response import ok

router = APIRouter(prefix="/faq", tags=["FAQ"])


def _faq(e) -> dict:
    return FaqResponse(
        id=str(e.id),
        question=e.question,
        answer=e.answer,
        subject=e.subject,
        grade=e.grade,
        hit_count=e.hit_count,
    ).model_dump(mode="json")


@router.get("", response_model=None)
async def list_faqs(
    request: Request,
    _: Annotated[UserResponse, Depends(get_current_user)],
    svc: Annotated[FaqService, Depends(get_faq_service)],
    subject: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
):
    entries = await svc.list_top(subject, limit)
    return ok([_faq(e) for e in entries], request_id=request.state.request_id)


@router.get("/search", response_model=None)
async def search_faqs(
    request: Request,
    _: Annotated[UserResponse, Depends(get_current_user)],
    svc: Annotated[FaqService, Depends(get_faq_service)],
    q: str = Query(min_length=1),
    limit: int = Query(default=20, ge=1, le=100),
):
    entries = await svc.search(q, limit)
    return ok([_faq(e) for e in entries], request_id=request.state.request_id)
