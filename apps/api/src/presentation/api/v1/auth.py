from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request

from src.application.dtos.auth import (
    ChangePasswordRequest,
    EmailVerifyConfirm,
    LoginRequest,
    PasswordResetConfirm,
    PasswordResetRequest,
    RefreshRequest,
    RegisterRequest,
)
from src.application.dtos.user import UserResponse
from src.application.interfaces.dependencies import get_auth_service, get_current_user
from src.application.services.auth_service import AuthService
from src.presentation.api.response import ok

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _client_meta(request: Request) -> tuple[str | None, str | None]:
    ip = request.client.host if request.client else None
    return ip, request.headers.get("user-agent")


@router.post("/register", status_code=201)
async def register(
    body: RegisterRequest,
    request: Request,
    auth: Annotated[AuthService, Depends(get_auth_service)],
):
    user, token = await auth.register(body)
    ip, agent = _client_meta(request)
    refresh = await auth.issue_refresh_token(UUID(user.id), ip, agent)
    await auth.request_email_verification(UUID(user.id))
    return ok(
        {"user": user.model_dump(), "token": token, "refresh_token": refresh},
        message="Account created successfully",
        request_id=request.state.request_id,
        status_code=201,
    )


@router.post("/login")
async def login(
    body: LoginRequest,
    request: Request,
    auth: Annotated[AuthService, Depends(get_auth_service)],
):
    user, token = await auth.login(body)
    ip, agent = _client_meta(request)
    refresh = await auth.issue_refresh_token(UUID(user.id), ip, agent)
    return ok(
        {"user": user.model_dump(), "token": token, "refresh_token": refresh},
        message="Login successful",
        request_id=request.state.request_id,
    )


@router.post("/refresh")
async def refresh(
    body: RefreshRequest,
    request: Request,
    auth: Annotated[AuthService, Depends(get_auth_service)],
):
    user, token, new_refresh = await auth.refresh_access_token(body.refresh_token)
    return ok(
        {"user": user.model_dump(), "token": token, "refresh_token": new_refresh},
        message="Token refreshed",
        request_id=request.state.request_id,
    )


@router.post("/logout")
async def logout(
    request: Request,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    auth: Annotated[AuthService, Depends(get_auth_service)],
    body: RefreshRequest | None = None,
):
    # Access JWT is stateless; revoke the server-side refresh session if the
    # client sends it, otherwise logout stays client-side (discard the token).
    if body:
        await auth.revoke_refresh_token(body.refresh_token)
    return ok({}, message="Logged out successfully", request_id=request.state.request_id)


@router.post("/password-reset/request")
async def password_reset_request(
    body: PasswordResetRequest,
    request: Request,
    auth: Annotated[AuthService, Depends(get_auth_service)],
):
    await auth.request_password_reset(body.email)
    return ok(
        {},
        message="If that email is registered, a reset link has been sent",
        request_id=request.state.request_id,
    )


@router.post("/password-reset/confirm")
async def password_reset_confirm(
    body: PasswordResetConfirm,
    request: Request,
    auth: Annotated[AuthService, Depends(get_auth_service)],
):
    await auth.confirm_password_reset(body.token, body.new_password)
    return ok({}, message="Password has been reset", request_id=request.state.request_id)


@router.post("/change-password")
async def change_password(
    body: ChangePasswordRequest,
    request: Request,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    auth: Annotated[AuthService, Depends(get_auth_service)],
):
    await auth.change_password(UUID(current_user.id), body.current_password, body.new_password)
    return ok({}, message="Password changed", request_id=request.state.request_id)


@router.post("/verify-email/request")
async def verify_email_request(
    request: Request,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    auth: Annotated[AuthService, Depends(get_auth_service)],
):
    await auth.request_email_verification(UUID(current_user.id))
    return ok({}, message="Verification email sent", request_id=request.state.request_id)


@router.post("/verify-email/confirm")
async def verify_email_confirm(
    body: EmailVerifyConfirm,
    request: Request,
    auth: Annotated[AuthService, Depends(get_auth_service)],
):
    user = await auth.confirm_email_verification(body.token)
    return ok(
        user.model_dump(), message="Email verified", request_id=request.state.request_id
    )


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
