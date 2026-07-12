"""Admin-only endpoints: institutions, users, classrooms, audit logs, storage, vector stats."""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request

from src.application.dtos.admin import (
    CreateInstitutionRequest,
    UpdateInstitutionRequest,
)
from src.application.dtos.user import UserResponse
from src.application.interfaces.dependencies import (
    get_admin_service,
    get_vector_service,
    require_admin,
)
from src.application.services.admin_service import AdminService
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


# ── Institutions ─────────────────────────────────────────────────────────────

@router.post("/institutions", status_code=201)
async def create_institution(
    body: CreateInstitutionRequest,
    request: Request,
    admin: Annotated[UserResponse, Depends(require_admin)],
    svc: Annotated[AdminService, Depends(get_admin_service)],
):
    result = await svc.create_institution(UUID(admin.id), body)
    return ok(result.model_dump(), message="Institution created", request_id=request.state.request_id, status_code=201)


@router.get("/institutions")
async def list_institutions(
    request: Request,
    _: Annotated[UserResponse, Depends(require_admin)],
    svc: Annotated[AdminService, Depends(get_admin_service)],
    search: str | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
):
    items, total = await svc.list_institutions(page=page, limit=limit, search=search)
    return ok(
        {"items": [i.model_dump() for i in items], "total": total, "page": page, "limit": limit},
        request_id=request.state.request_id,
    )


@router.patch("/institutions/{institution_id}")
async def update_institution(
    institution_id: UUID,
    body: UpdateInstitutionRequest,
    request: Request,
    admin: Annotated[UserResponse, Depends(require_admin)],
    svc: Annotated[AdminService, Depends(get_admin_service)],
):
    result = await svc.update_institution(UUID(admin.id), institution_id, body)
    return ok(result.model_dump(), message="Institution updated", request_id=request.state.request_id)


@router.delete("/institutions/{institution_id}")
async def delete_institution(
    institution_id: UUID,
    request: Request,
    admin: Annotated[UserResponse, Depends(require_admin)],
    svc: Annotated[AdminService, Depends(get_admin_service)],
):
    await svc.delete_institution(UUID(admin.id), institution_id)
    return ok({}, message="Institution deleted", request_id=request.state.request_id)


# ── Users ────────────────────────────────────────────────────────────────────

@router.get("/users")
async def list_users(
    request: Request,
    _: Annotated[UserResponse, Depends(require_admin)],
    svc: Annotated[AdminService, Depends(get_admin_service)],
    role: str | None = None,
    search: str | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
):
    result = await svc.list_users(page=page, limit=limit, role=role, search=search)
    return ok(result.model_dump(), request_id=request.state.request_id)


@router.post("/users/{user_id}/suspend")
async def suspend_user(
    user_id: UUID,
    request: Request,
    admin: Annotated[UserResponse, Depends(require_admin)],
    svc: Annotated[AdminService, Depends(get_admin_service)],
):
    result = await svc.suspend_user(UUID(admin.id), user_id)
    return ok(result.model_dump(), message="User suspended", request_id=request.state.request_id)


@router.post("/users/{user_id}/reactivate")
async def reactivate_user(
    user_id: UUID,
    request: Request,
    admin: Annotated[UserResponse, Depends(require_admin)],
    svc: Annotated[AdminService, Depends(get_admin_service)],
):
    result = await svc.reactivate_user(UUID(admin.id), user_id)
    return ok(result.model_dump(), message="User reactivated", request_id=request.state.request_id)


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: UUID,
    request: Request,
    admin: Annotated[UserResponse, Depends(require_admin)],
    svc: Annotated[AdminService, Depends(get_admin_service)],
):
    await svc.delete_user(UUID(admin.id), user_id)
    return ok({}, message="User deleted", request_id=request.state.request_id)


# ── Classrooms ───────────────────────────────────────────────────────────────

@router.get("/classrooms")
async def list_classrooms(
    request: Request,
    _: Annotated[UserResponse, Depends(require_admin)],
    svc: Annotated[AdminService, Depends(get_admin_service)],
    search: str | None = None,
    include_deleted: bool = False,
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
):
    items, total = await svc.list_classrooms(
        page=page, limit=limit, search=search, include_deleted=include_deleted
    )
    return ok(
        {"items": items, "total": total, "page": page, "limit": limit},
        request_id=request.state.request_id,
    )


@router.post("/classrooms/{classroom_id}/restore")
async def restore_classroom(
    classroom_id: UUID,
    request: Request,
    admin: Annotated[UserResponse, Depends(require_admin)],
    svc: Annotated[AdminService, Depends(get_admin_service)],
):
    await svc.restore_classroom(UUID(admin.id), classroom_id)
    return ok({}, message="Classroom restored", request_id=request.state.request_id)


# ── Audit & storage ──────────────────────────────────────────────────────────

@router.get("/audit-logs")
async def list_audit_logs(
    request: Request,
    _: Annotated[UserResponse, Depends(require_admin)],
    svc: Annotated[AdminService, Depends(get_admin_service)],
    user_id: UUID | None = None,
    action: str | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
):
    items, total = await svc.list_audit_logs(
        user_id=user_id, action=action, page=page, limit=limit
    )
    return ok(
        {"items": items, "total": total, "page": page, "limit": limit},
        request_id=request.state.request_id,
    )


@router.get("/storage-usage")
async def storage_usage(
    request: Request,
    _: Annotated[UserResponse, Depends(require_admin)],
    svc: Annotated[AdminService, Depends(get_admin_service)],
):
    result = await svc.storage_usage()
    return ok(result, request_id=request.state.request_id)
