from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request

from src.application.dtos.parent import (
    ChildSummaryResponse,
    GuardianSummaryResponse,
    LinkCodeResponse,
    LinkRequest,
)
from src.application.dtos.user import UserResponse
from src.application.interfaces.dependencies import get_current_user, get_parent_service
from src.application.services.parent_service import ParentService
from src.presentation.api.response import ok

router = APIRouter(prefix="/parent", tags=["Parent Portal"])


# ── Student side ─────────────────────────────────────────────────────────────


@router.post("/link-code", response_model=None)
async def issue_link_code(
    request: Request,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    svc: Annotated[ParentService, Depends(get_parent_service)],
):
    code, ttl = await svc.generate_link_code(UUID(current_user.id))
    return ok(
        LinkCodeResponse(code=code, expires_in_seconds=ttl).model_dump(mode="json"),
        request_id=request.state.request_id,
    )


@router.get("/guardians", response_model=None)
async def my_guardians(
    request: Request,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    svc: Annotated[ParentService, Depends(get_parent_service)],
):
    guardians = await svc.list_guardians(UUID(current_user.id))
    data = [
        GuardianSummaryResponse(
            link_id=str(link.id),
            parent_id=str(link.parent_id),
            username=username,
            email=email,
            linked_at=link.created_at.isoformat(),
        ).model_dump(mode="json")
        for link, username, email in guardians
    ]
    return ok(data, request_id=request.state.request_id)


@router.delete("/guardians/{parent_id}", response_model=None)
async def revoke_guardian(
    parent_id: str,
    request: Request,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    svc: Annotated[ParentService, Depends(get_parent_service)],
):
    await svc.revoke_guardian(UUID(current_user.id), UUID(parent_id))
    return ok({"revoked": True}, request_id=request.state.request_id)


# ── Parent side ──────────────────────────────────────────────────────────────


@router.post("/link", response_model=None)
async def link_child(
    body: LinkRequest,
    request: Request,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    svc: Annotated[ParentService, Depends(get_parent_service)],
):
    student_id, username = await svc.link_by_code(UUID(current_user.id), body.code)
    return ok(
        {"student_id": str(student_id), "username": username},
        request_id=request.state.request_id,
    )


@router.get("/children", response_model=None)
async def my_children(
    request: Request,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    svc: Annotated[ParentService, Depends(get_parent_service)],
):
    children = await svc.list_children(UUID(current_user.id))
    data = [
        ChildSummaryResponse(
            link_id=str(link.id),
            student_id=str(link.student_id),
            username=username,
            email=email,
            grade=grade,
            linked_at=link.created_at.isoformat(),
        ).model_dump(mode="json")
        for link, username, email, grade in children
    ]
    return ok(data, request_id=request.state.request_id)


@router.get("/children/{student_id}/overview", response_model=None)
async def child_overview(
    student_id: str,
    request: Request,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    svc: Annotated[ParentService, Depends(get_parent_service)],
):
    overview = await svc.child_overview(UUID(current_user.id), UUID(student_id))
    return ok(overview, request_id=request.state.request_id)
