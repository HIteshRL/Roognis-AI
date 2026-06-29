from typing import Annotated

from fastapi import APIRouter, Depends, Request

from src.application.dtos.knowledge import SearchRequest
from src.application.dtos.user import UserResponse
from src.application.interfaces.dependencies import get_current_user, get_search_service
from src.application.services.search_service import SearchService
from src.presentation.api.response import ok

router = APIRouter(prefix="/search", tags=["Search"])


@router.post("")
async def search(
    body: SearchRequest,
    request: Request,
    _: Annotated[UserResponse, Depends(get_current_user)],
    svc: Annotated[SearchService, Depends(get_search_service)],
):
    result = await svc.search(body)
    return ok(result.model_dump(), request_id=request.state.request_id)
