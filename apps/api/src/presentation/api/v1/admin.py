"""Admin-only endpoints: vector stats, processing queue overview, cache control."""
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from src.application.dtos.user import UserResponse
from src.application.interfaces.dependencies import (
    get_caching_engine,
    get_vector_service,
    require_admin,
)
from src.application.services.caching_engine import CachingEngine
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


@router.get("/cache/stats")
async def cache_stats(
    request: Request,
    _: Annotated[UserResponse, Depends(require_admin)],
    engine: Annotated[CachingEngine, Depends(get_caching_engine)],
):
    return ok(await engine.stats(), request_id=request.state.request_id)


@router.post("/cache/invalidate")
async def cache_invalidate(
    request: Request,
    _: Annotated[UserResponse, Depends(require_admin)],
    engine: Annotated[CachingEngine, Depends(get_caching_engine)],
    subject: str | None = Query(default=None),
):
    version = await engine.invalidate_scope(subject)
    return ok(
        {"invalidated_scope": subject or "global", "new_version": version},
        request_id=request.state.request_id,
    )
