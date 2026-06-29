from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request

from src.application.dtos.knowledge import CreateKnowledgeBaseRequest
from src.application.dtos.user import UserResponse
from src.application.interfaces.dependencies import (
    get_current_user,
    get_knowledge_library_service,
    require_admin,
)
from src.application.services.knowledge_library_service import KnowledgeLibraryService
from src.presentation.api.response import ok, paginated

router = APIRouter(prefix="/library", tags=["Knowledge Library"])


@router.post("", status_code=201)
async def create_knowledge_base(
    body: CreateKnowledgeBaseRequest,
    request: Request,
    admin: Annotated[UserResponse, Depends(require_admin)],
    svc: Annotated[KnowledgeLibraryService, Depends(get_knowledge_library_service)],
):
    kb = await svc.create(body, UUID(admin.id))
    return ok(kb.model_dump(), message="Knowledge base created", request_id=request.state.request_id, status_code=201)


@router.get("")
async def list_knowledge_bases(
    request: Request,
    _: Annotated[UserResponse, Depends(get_current_user)],
    svc: Annotated[KnowledgeLibraryService, Depends(get_knowledge_library_service)],
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
):
    kbs, total = await svc.list(page, limit)
    return paginated(
        data=[kb.model_dump() for kb in kbs],
        total=total,
        page=page,
        limit=limit,
        request_id=request.state.request_id,
    )


@router.get("/{kb_id}")
async def get_knowledge_base(
    kb_id: UUID,
    request: Request,
    _: Annotated[UserResponse, Depends(get_current_user)],
    svc: Annotated[KnowledgeLibraryService, Depends(get_knowledge_library_service)],
):
    kb = await svc.get(kb_id)
    return ok(kb.model_dump(), request_id=request.state.request_id)


@router.delete("/{kb_id}")
async def delete_knowledge_base(
    kb_id: UUID,
    request: Request,
    _: Annotated[UserResponse, Depends(require_admin)],
    svc: Annotated[KnowledgeLibraryService, Depends(get_knowledge_library_service)],
):
    await svc.delete(kb_id)
    return ok({}, message="Knowledge base deleted", request_id=request.state.request_id)
