"""
/student/classrooms — student side of the Google Classroom model.

Students join a classroom with a code, see their enrolled classes, and list a
class's chapters. Per-chapter inference is served by the chat endpoint, which
accepts a chapter_id and scopes retrieval to that chapter's knowledge base.
"""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request

from src.application.dtos.classroom import JoinClassroomRequest
from src.application.dtos.user import UserResponse
from src.application.interfaces.dependencies import (
    get_classroom_service,
    get_current_user,
)
from src.application.services.classroom_service import ClassroomService
from src.presentation.api.response import ok

router = APIRouter(prefix="/student/classrooms", tags=["Classrooms (Student)"])


@router.post("/join", status_code=201)
async def join_classroom(
    body: JoinClassroomRequest,
    request: Request,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    svc: Annotated[ClassroomService, Depends(get_classroom_service)],
):
    result = await svc.join_by_code(UUID(current_user.id), body.join_code)
    return ok(result.model_dump(), message="Joined class", request_id=request.state.request_id, status_code=201)


@router.get("")
async def list_my_classrooms(
    request: Request,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    svc: Annotated[ClassroomService, Depends(get_classroom_service)],
):
    result = await svc.list_student_classrooms(UUID(current_user.id))
    return ok([r.model_dump() for r in result], request_id=request.state.request_id)


@router.get("/{classroom_id}/chapters")
async def list_classroom_chapters(
    classroom_id: UUID,
    request: Request,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    svc: Annotated[ClassroomService, Depends(get_classroom_service)],
):
    result = await svc.list_chapters_for_student(UUID(current_user.id), classroom_id)
    return ok([r.model_dump() for r in result], request_id=request.state.request_id)
