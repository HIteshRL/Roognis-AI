"""Coursework endpoints — teacher lifecycle management + student stream."""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request

from src.application.dtos.coursework import (
    AddAttachmentRequest,
    CreateCourseworkRequest,
    PollVoteRequest,
    ScheduleRequest,
    UpdateCourseworkRequest,
)
from src.application.dtos.user import UserResponse
from src.application.interfaces.dependencies import (
    get_coursework_service,
    get_current_user,
    require_teacher,
)
from src.application.services.coursework_service import CourseworkService
from src.presentation.api.response import ok

teacher_router = APIRouter(prefix="/teacher", tags=["Coursework (Teacher)"])
student_router = APIRouter(prefix="/student", tags=["Coursework (Student)"])


# ── Teacher ──────────────────────────────────────────────────────────────────

@teacher_router.post("/classrooms/{classroom_id}/coursework", status_code=201)
async def create_coursework(
    classroom_id: UUID,
    body: CreateCourseworkRequest,
    request: Request,
    teacher: Annotated[UserResponse, Depends(require_teacher)],
    svc: Annotated[CourseworkService, Depends(get_coursework_service)],
):
    result = await svc.create(UUID(teacher.id), classroom_id, body)
    return ok(result.model_dump(), message="Created", request_id=request.state.request_id, status_code=201)


@teacher_router.get("/classrooms/{classroom_id}/coursework")
async def list_coursework_teacher(
    classroom_id: UUID,
    request: Request,
    teacher: Annotated[UserResponse, Depends(require_teacher)],
    svc: Annotated[CourseworkService, Depends(get_coursework_service)],
    type: str | None = None,
    status: str | None = None,
    search: str | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
):
    result = await svc.list_for_teacher(
        UUID(teacher.id), classroom_id, type=type, status=status,
        search=search, page=page, limit=limit,
    )
    return ok(result.model_dump(), request_id=request.state.request_id)


@teacher_router.get("/coursework/{coursework_id}")
async def get_coursework_teacher(
    coursework_id: UUID,
    request: Request,
    teacher: Annotated[UserResponse, Depends(require_teacher)],
    svc: Annotated[CourseworkService, Depends(get_coursework_service)],
):
    result = await svc.get_for_user(UUID(teacher.id), coursework_id, as_teacher=True)
    return ok(result.model_dump(), request_id=request.state.request_id)


@teacher_router.patch("/coursework/{coursework_id}")
async def update_coursework(
    coursework_id: UUID,
    body: UpdateCourseworkRequest,
    request: Request,
    teacher: Annotated[UserResponse, Depends(require_teacher)],
    svc: Annotated[CourseworkService, Depends(get_coursework_service)],
):
    result = await svc.update(UUID(teacher.id), coursework_id, body)
    return ok(result.model_dump(), message="Updated", request_id=request.state.request_id)


@teacher_router.post("/coursework/{coursework_id}/publish")
async def publish_coursework(
    coursework_id: UUID,
    request: Request,
    teacher: Annotated[UserResponse, Depends(require_teacher)],
    svc: Annotated[CourseworkService, Depends(get_coursework_service)],
):
    result = await svc.publish(UUID(teacher.id), coursework_id)
    return ok(result.model_dump(), message="Published", request_id=request.state.request_id)


@teacher_router.post("/coursework/{coursework_id}/schedule")
async def schedule_coursework(
    coursework_id: UUID,
    body: ScheduleRequest,
    request: Request,
    teacher: Annotated[UserResponse, Depends(require_teacher)],
    svc: Annotated[CourseworkService, Depends(get_coursework_service)],
):
    result = await svc.schedule(UUID(teacher.id), coursework_id, body.scheduled_at)
    return ok(result.model_dump(), message="Scheduled", request_id=request.state.request_id)


@teacher_router.post("/coursework/{coursework_id}/archive")
async def archive_coursework(
    coursework_id: UUID,
    request: Request,
    teacher: Annotated[UserResponse, Depends(require_teacher)],
    svc: Annotated[CourseworkService, Depends(get_coursework_service)],
):
    result = await svc.archive(UUID(teacher.id), coursework_id)
    return ok(result.model_dump(), message="Archived", request_id=request.state.request_id)


@teacher_router.post("/coursework/{coursework_id}/duplicate", status_code=201)
async def duplicate_coursework(
    coursework_id: UUID,
    request: Request,
    teacher: Annotated[UserResponse, Depends(require_teacher)],
    svc: Annotated[CourseworkService, Depends(get_coursework_service)],
):
    result = await svc.duplicate(UUID(teacher.id), coursework_id)
    return ok(result.model_dump(), message="Duplicated", request_id=request.state.request_id, status_code=201)


@teacher_router.delete("/coursework/{coursework_id}")
async def delete_coursework(
    coursework_id: UUID,
    request: Request,
    teacher: Annotated[UserResponse, Depends(require_teacher)],
    svc: Annotated[CourseworkService, Depends(get_coursework_service)],
):
    await svc.delete(UUID(teacher.id), coursework_id)
    return ok({}, message="Deleted", request_id=request.state.request_id)


@teacher_router.post("/coursework/{coursework_id}/attachments", status_code=201)
async def add_attachment(
    coursework_id: UUID,
    body: AddAttachmentRequest,
    request: Request,
    teacher: Annotated[UserResponse, Depends(require_teacher)],
    svc: Annotated[CourseworkService, Depends(get_coursework_service)],
):
    result = await svc.add_attachment(UUID(teacher.id), coursework_id, body)
    return ok(result.model_dump(), message="Attachment added", request_id=request.state.request_id, status_code=201)


@teacher_router.delete("/coursework/{coursework_id}/attachments/{attachment_id}")
async def remove_attachment(
    coursework_id: UUID,
    attachment_id: UUID,
    request: Request,
    teacher: Annotated[UserResponse, Depends(require_teacher)],
    svc: Annotated[CourseworkService, Depends(get_coursework_service)],
):
    await svc.remove_attachment(UUID(teacher.id), coursework_id, attachment_id)
    return ok({}, message="Attachment removed", request_id=request.state.request_id)


# ── Student ──────────────────────────────────────────────────────────────────

@student_router.get("/classrooms/{classroom_id}/coursework")
async def list_coursework_student(
    classroom_id: UUID,
    request: Request,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    svc: Annotated[CourseworkService, Depends(get_coursework_service)],
    type: str | None = None,
    search: str | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
):
    result = await svc.list_for_student(
        UUID(current_user.id), classroom_id, type=type, search=search, page=page, limit=limit
    )
    return ok(result.model_dump(), request_id=request.state.request_id)


@student_router.get("/coursework/{coursework_id}")
async def get_coursework_student(
    coursework_id: UUID,
    request: Request,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    svc: Annotated[CourseworkService, Depends(get_coursework_service)],
):
    result = await svc.get_for_user(UUID(current_user.id), coursework_id, as_teacher=False)
    return ok(result.model_dump(), request_id=request.state.request_id)


@student_router.post("/coursework/{coursework_id}/vote")
async def vote_poll(
    coursework_id: UUID,
    body: PollVoteRequest,
    request: Request,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    svc: Annotated[CourseworkService, Depends(get_coursework_service)],
):
    results = await svc.vote(UUID(current_user.id), coursework_id, body.option_index)
    return ok({"results": results}, message="Vote recorded", request_id=request.state.request_id)
