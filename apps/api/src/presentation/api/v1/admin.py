"""Admin-only endpoints: vector stats, processing queue overview."""
from typing import Annotated

from fastapi import APIRouter, Depends, Request

from src.application.dtos.user import UserResponse
from src.application.interfaces.dependencies import (
    get_vector_service,
    require_admin,
)
from src.application.services.vector_service import VectorService
from src.presentation.api.response import ok

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/vector/stats")
async def vector_stats(
    request: Request,
    _: Annotated[UserResponse, Depends(require_admin)],
    vector_svc: Annotated[VectorService, Depends(get_vector_service)],
):
    stats = await vector_svc.collection_stats()
    return ok(stats, request_id=request.state.request_id)
