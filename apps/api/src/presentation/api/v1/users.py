from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request

from src.application.dtos.user import UpdateProfileRequest, UpdateSettingsRequest, UserResponse
from src.application.interfaces.dependencies import get_current_user, get_user_service
from src.application.services.user_service import UserService
from src.presentation.api.response import ok

router = APIRouter(tags=["Users"])


@router.get("/profile")
async def get_profile(
    request: Request,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    svc: Annotated[UserService, Depends(get_user_service)],
):
    profile = await svc.get_profile(UUID(current_user.id))
    return ok(profile.model_dump(), request_id=request.state.request_id)


@router.put("/profile")
async def update_profile(
    body: UpdateProfileRequest,
    request: Request,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    svc: Annotated[UserService, Depends(get_user_service)],
):
    profile = await svc.update_profile(UUID(current_user.id), body)
    return ok(profile.model_dump(), message="Profile updated", request_id=request.state.request_id)


@router.get("/settings")
async def get_settings(
    request: Request,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    svc: Annotated[UserService, Depends(get_user_service)],
):
    settings = await svc.get_settings(UUID(current_user.id))
    return ok(settings.model_dump(), request_id=request.state.request_id)


@router.put("/settings")
async def update_settings(
    body: UpdateSettingsRequest,
    request: Request,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    svc: Annotated[UserService, Depends(get_user_service)],
):
    settings = await svc.update_settings(UUID(current_user.id), body)
    return ok(
        settings.model_dump(), message="Settings updated", request_id=request.state.request_id
    )
