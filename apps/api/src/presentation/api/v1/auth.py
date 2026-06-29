from typing import Annotated

from fastapi import APIRouter, Depends, Request

from src.application.dtos.auth import LoginRequest, RegisterRequest
from src.application.interfaces.dependencies import get_auth_service, get_current_user
from src.application.services.auth_service import AuthService
from src.application.dtos.user import UserResponse
from src.presentation.api.response import ok

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", status_code=201)
async def register(
    body: RegisterRequest,
    request: Request,
    auth: Annotated[AuthService, Depends(get_auth_service)],
):
    user, token = await auth.register(body)
    return ok(
        {"user": user.model_dump(), "token": token},
        message="Account created successfully",
        request_id=request.state.request_id,
    )


@router.post("/login")
async def login(
    body: LoginRequest,
    request: Request,
    auth: Annotated[AuthService, Depends(get_auth_service)],
):
    user, token = await auth.login(body)
    return ok(
        {"user": user.model_dump(), "token": token},
        message="Login successful",
        request_id=request.state.request_id,
    )


@router.post("/logout")
async def logout(
    request: Request,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
):
    # JWT is stateless; logout is handled client-side by discarding the token.
    # Future: add token to a Redis denylist here if needed.
    return ok({}, message="Logged out successfully", request_id=request.state.request_id)


@router.get("/me")
async def me(
    request: Request,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
):
    return ok(
        current_user.model_dump(),
        message="",
        request_id=request.state.request_id,
    )
