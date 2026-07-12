"""/notifications — per-user notification center (both portals)."""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request

from src.application.dtos.user import UserResponse
from src.application.interfaces.dependencies import (
    get_current_user,
    get_notification_service,
)
from src.application.services.notification_service import NotificationService
from src.presentation.api.response import ok

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("")
async def list_notifications(
    request: Request,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    svc: Annotated[NotificationService, Depends(get_notification_service)],
    unread_only: bool = False,
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
):
    result = await svc.list_for_user(
        UUID(current_user.id), unread_only=unread_only, page=page, limit=limit
    )
    return ok(result.model_dump(), request_id=request.state.request_id)


@router.get("/unread-count")
async def unread_count(
    request: Request,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    svc: Annotated[NotificationService, Depends(get_notification_service)],
):
    count = await svc.unread_count(UUID(current_user.id))
    return ok({"unread_count": count}, request_id=request.state.request_id)


@router.post("/{notification_id}/read")
async def mark_read(
    notification_id: UUID,
    request: Request,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    svc: Annotated[NotificationService, Depends(get_notification_service)],
):
    await svc.mark_read(UUID(current_user.id), notification_id)
    return ok({}, message="Marked read", request_id=request.state.request_id)


@router.post("/read-all")
async def mark_all_read(
    request: Request,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    svc: Annotated[NotificationService, Depends(get_notification_service)],
):
    await svc.mark_all_read(UUID(current_user.id))
    return ok({}, message="All notifications marked read", request_id=request.state.request_id)
