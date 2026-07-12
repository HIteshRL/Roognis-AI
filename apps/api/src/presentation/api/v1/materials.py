"""
Classroom materials — teacher management + student consumption.

Teacher routes live under /teacher/…, student routes under /student/…; both
share MaterialService, which enforces teach/enrollment access per call.
"""
from typing import Annotated
from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile
from fastapi.responses import Response

from src.application.dtos.material import (
    CreateFolderRequest,
    CreateLinkMaterialRequest,
    MoveMaterialRequest,
    RecordViewRequest,
    UpdateFolderRequest,
    UpdateMaterialRequest,
)
from src.application.dtos.user import UserResponse
from src.application.interfaces.dependencies import (
    get_current_user,
    get_material_service,
    require_teacher,
)
from src.application.services.material_service import MaterialService
from src.presentation.api.response import ok

teacher_router = APIRouter(prefix="/teacher", tags=["Materials (Teacher)"])
student_router = APIRouter(prefix="/student", tags=["Materials (Student)"])


# ── Teacher: folders ─────────────────────────────────────────────────────────

@teacher_router.post("/classrooms/{classroom_id}/folders", status_code=201)
async def create_folder(
    classroom_id: UUID,
    body: CreateFolderRequest,
    request: Request,
    teacher: Annotated[UserResponse, Depends(require_teacher)],
    svc: Annotated[MaterialService, Depends(get_material_service)],
):
    result = await svc.create_folder(UUID(teacher.id), classroom_id, body)
    return ok(result.model_dump(), message="Folder created", request_id=request.state.request_id, status_code=201)


@teacher_router.get("/classrooms/{classroom_id}/folders")
async def list_folders(
    classroom_id: UUID,
    request: Request,
    teacher: Annotated[UserResponse, Depends(require_teacher)],
    svc: Annotated[MaterialService, Depends(get_material_service)],
):
    result = await svc.list_folders(UUID(teacher.id), classroom_id, as_teacher=True)
    return ok([r.model_dump() for r in result], request_id=request.state.request_id)


@teacher_router.patch("/folders/{folder_id}")
async def update_folder(
    folder_id: UUID,
    body: UpdateFolderRequest,
    request: Request,
    teacher: Annotated[UserResponse, Depends(require_teacher)],
    svc: Annotated[MaterialService, Depends(get_material_service)],
):
    result = await svc.update_folder(UUID(teacher.id), folder_id, body)
    return ok(result.model_dump(), message="Folder updated", request_id=request.state.request_id)


@teacher_router.delete("/folders/{folder_id}")
async def delete_folder(
    folder_id: UUID,
    request: Request,
    teacher: Annotated[UserResponse, Depends(require_teacher)],
    svc: Annotated[MaterialService, Depends(get_material_service)],
):
    await svc.delete_folder(UUID(teacher.id), folder_id)
    return ok({}, message="Folder deleted", request_id=request.state.request_id)


@teacher_router.post("/folders/{folder_id}/restore")
async def restore_folder(
    folder_id: UUID,
    request: Request,
    teacher: Annotated[UserResponse, Depends(require_teacher)],
    svc: Annotated[MaterialService, Depends(get_material_service)],
):
    result = await svc.restore_folder(UUID(teacher.id), folder_id)
    return ok(result.model_dump(), message="Folder restored", request_id=request.state.request_id)


# ── Teacher: materials ───────────────────────────────────────────────────────

@teacher_router.post("/classrooms/{classroom_id}/materials", status_code=201)
async def upload_material(
    classroom_id: UUID,
    request: Request,
    teacher: Annotated[UserResponse, Depends(require_teacher)],
    svc: Annotated[MaterialService, Depends(get_material_service)],
    file: Annotated[UploadFile, File()],
    title: Annotated[str | None, Form()] = None,
    description: Annotated[str | None, Form()] = None,
    category: Annotated[str, Form()] = "other",
    folder_id: Annotated[str | None, Form()] = None,
):
    file_bytes = await file.read()
    result = await svc.upload_material(
        teacher_id=UUID(teacher.id),
        classroom_id=classroom_id,
        filename=file.filename or "upload",
        file_bytes=file_bytes,
        content_type=file.content_type or "",
        title=title,
        description=description,
        category=category,
        folder_id=UUID(folder_id) if folder_id else None,
    )
    return ok(result.model_dump(), message="Material uploaded", request_id=request.state.request_id, status_code=201)


@teacher_router.post("/classrooms/{classroom_id}/materials/link", status_code=201)
async def create_link_material(
    classroom_id: UUID,
    body: CreateLinkMaterialRequest,
    request: Request,
    teacher: Annotated[UserResponse, Depends(require_teacher)],
    svc: Annotated[MaterialService, Depends(get_material_service)],
):
    result = await svc.create_link_material(UUID(teacher.id), classroom_id, body)
    return ok(result.model_dump(), message="Link added", request_id=request.state.request_id, status_code=201)


@teacher_router.get("/classrooms/{classroom_id}/materials")
async def list_materials_teacher(
    classroom_id: UUID,
    request: Request,
    teacher: Annotated[UserResponse, Depends(require_teacher)],
    svc: Annotated[MaterialService, Depends(get_material_service)],
    folder_id: UUID | None = None,
    category: str | None = None,
    search: str | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    sort: str = "created_at",
    order: str = "desc",
):
    result = await svc.list_materials(
        UUID(teacher.id), classroom_id, as_teacher=True,
        folder_id=folder_id, category=category, search=search,
        page=page, limit=limit, sort=sort, descending=order != "asc",
    )
    return ok(result.model_dump(), request_id=request.state.request_id)


@teacher_router.get("/classrooms/{classroom_id}/materials/trash")
async def list_material_trash(
    classroom_id: UUID,
    request: Request,
    teacher: Annotated[UserResponse, Depends(require_teacher)],
    svc: Annotated[MaterialService, Depends(get_material_service)],
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
):
    result = await svc.list_trash(UUID(teacher.id), classroom_id, page=page, limit=limit)
    return ok(result.model_dump(), request_id=request.state.request_id)


@teacher_router.patch("/materials/{material_id}")
async def update_material(
    material_id: UUID,
    body: UpdateMaterialRequest,
    request: Request,
    teacher: Annotated[UserResponse, Depends(require_teacher)],
    svc: Annotated[MaterialService, Depends(get_material_service)],
):
    result = await svc.update_material(UUID(teacher.id), material_id, body)
    return ok(result.model_dump(), message="Material updated", request_id=request.state.request_id)


@teacher_router.post("/materials/{material_id}/move")
async def move_material(
    material_id: UUID,
    body: MoveMaterialRequest,
    request: Request,
    teacher: Annotated[UserResponse, Depends(require_teacher)],
    svc: Annotated[MaterialService, Depends(get_material_service)],
):
    result = await svc.move_material(
        UUID(teacher.id), material_id, UUID(body.folder_id) if body.folder_id else None
    )
    return ok(result.model_dump(), message="Material moved", request_id=request.state.request_id)


@teacher_router.post("/materials/{material_id}/versions", status_code=201)
async def upload_material_version(
    material_id: UUID,
    request: Request,
    teacher: Annotated[UserResponse, Depends(require_teacher)],
    svc: Annotated[MaterialService, Depends(get_material_service)],
    file: Annotated[UploadFile, File()],
):
    file_bytes = await file.read()
    result = await svc.upload_new_version(
        UUID(teacher.id), material_id, file.filename or "upload",
        file_bytes, file.content_type or "",
    )
    return ok(result.model_dump(), message="New version uploaded", request_id=request.state.request_id, status_code=201)


@teacher_router.get("/materials/{material_id}/versions")
async def list_material_versions(
    material_id: UUID,
    request: Request,
    teacher: Annotated[UserResponse, Depends(require_teacher)],
    svc: Annotated[MaterialService, Depends(get_material_service)],
):
    result = await svc.list_versions(UUID(teacher.id), material_id)
    return ok([r.model_dump() for r in result], request_id=request.state.request_id)


@teacher_router.delete("/materials/{material_id}")
async def delete_material(
    material_id: UUID,
    request: Request,
    teacher: Annotated[UserResponse, Depends(require_teacher)],
    svc: Annotated[MaterialService, Depends(get_material_service)],
):
    await svc.delete_material(UUID(teacher.id), material_id)
    return ok({}, message="Material moved to trash", request_id=request.state.request_id)


@teacher_router.post("/materials/{material_id}/restore")
async def restore_material(
    material_id: UUID,
    request: Request,
    teacher: Annotated[UserResponse, Depends(require_teacher)],
    svc: Annotated[MaterialService, Depends(get_material_service)],
):
    result = await svc.restore_material(UUID(teacher.id), material_id)
    return ok(result.model_dump(), message="Material restored", request_id=request.state.request_id)


@teacher_router.delete("/materials/{material_id}/permanent")
async def purge_material(
    material_id: UUID,
    request: Request,
    teacher: Annotated[UserResponse, Depends(require_teacher)],
    svc: Annotated[MaterialService, Depends(get_material_service)],
):
    await svc.purge_material(UUID(teacher.id), material_id)
    return ok({}, message="Material permanently deleted", request_id=request.state.request_id)


@teacher_router.get("/materials/{material_id}/download")
async def download_material_teacher(
    material_id: UUID,
    teacher: Annotated[UserResponse, Depends(require_teacher)],
    svc: Annotated[MaterialService, Depends(get_material_service)],
):
    material, data = await svc.download(UUID(teacher.id), material_id, as_teacher=True)
    return _file_response(material.filename or "download", material.file_type, data)


# ── Student: materials ───────────────────────────────────────────────────────

@student_router.get("/classrooms/{classroom_id}/materials")
async def list_materials_student(
    classroom_id: UUID,
    request: Request,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    svc: Annotated[MaterialService, Depends(get_material_service)],
    folder_id: UUID | None = None,
    category: str | None = None,
    search: str | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    sort: str = "created_at",
    order: str = "desc",
):
    result = await svc.list_materials(
        UUID(current_user.id), classroom_id, as_teacher=False,
        folder_id=folder_id, category=category, search=search,
        page=page, limit=limit, sort=sort, descending=order != "asc",
    )
    return ok(result.model_dump(), request_id=request.state.request_id)


@student_router.get("/classrooms/{classroom_id}/folders")
async def list_folders_student(
    classroom_id: UUID,
    request: Request,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    svc: Annotated[MaterialService, Depends(get_material_service)],
):
    result = await svc.list_folders(UUID(current_user.id), classroom_id, as_teacher=False)
    return ok([r.model_dump() for r in result], request_id=request.state.request_id)


@student_router.get("/materials/{material_id}/download")
async def download_material_student(
    material_id: UUID,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    svc: Annotated[MaterialService, Depends(get_material_service)],
):
    material, data = await svc.download(UUID(current_user.id), material_id, as_teacher=False)
    return _file_response(material.filename or "download", material.file_type, data)


@student_router.post("/materials/{material_id}/bookmark")
async def bookmark_material(
    material_id: UUID,
    request: Request,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    svc: Annotated[MaterialService, Depends(get_material_service)],
):
    await svc.bookmark(UUID(current_user.id), material_id)
    return ok({}, message="Bookmarked", request_id=request.state.request_id)


@student_router.delete("/materials/{material_id}/bookmark")
async def unbookmark_material(
    material_id: UUID,
    request: Request,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    svc: Annotated[MaterialService, Depends(get_material_service)],
):
    await svc.unbookmark(UUID(current_user.id), material_id)
    return ok({}, message="Bookmark removed", request_id=request.state.request_id)


@student_router.get("/bookmarks")
async def list_bookmarks(
    request: Request,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    svc: Annotated[MaterialService, Depends(get_material_service)],
):
    result = await svc.list_bookmarks(UUID(current_user.id))
    return ok([r.model_dump() for r in result], request_id=request.state.request_id)


@student_router.post("/materials/{material_id}/view")
async def record_material_view(
    material_id: UUID,
    request: Request,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    svc: Annotated[MaterialService, Depends(get_material_service)],
    body: RecordViewRequest | None = None,
):
    await svc.record_view(
        UUID(current_user.id), material_id, body.progress if body else None
    )
    return ok({}, request_id=request.state.request_id)


@student_router.get("/materials/recently-viewed")
async def recently_viewed(
    request: Request,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    svc: Annotated[MaterialService, Depends(get_material_service)],
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
):
    result = await svc.recently_viewed(UUID(current_user.id), limit=limit)
    return ok([r.model_dump() for r in result], request_id=request.state.request_id)


@student_router.get("/materials/continue-reading")
async def continue_reading(
    request: Request,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    svc: Annotated[MaterialService, Depends(get_material_service)],
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
):
    result = await svc.continue_reading(UUID(current_user.id), limit=limit)
    return ok([r.model_dump() for r in result], request_id=request.state.request_id)


def _file_response(filename: str, content_type: str | None, data: bytes) -> Response:
    return Response(
        content=data,
        media_type=content_type or "application/octet-stream",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}",
        },
    )
