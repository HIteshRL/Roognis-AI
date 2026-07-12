"""Submission + grading endpoints. Multi-file uploads via multipart form."""
from typing import Annotated
from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile
from fastapi.responses import Response

from src.application.dtos.submission import GradeRequest
from src.application.dtos.user import UserResponse
from src.application.interfaces.dependencies import (
    get_current_user,
    get_submission_service,
    require_teacher,
)
from src.application.services.submission_service import SubmissionService
from src.presentation.api.response import ok

teacher_router = APIRouter(prefix="/teacher", tags=["Grading (Teacher)"])
student_router = APIRouter(prefix="/student", tags=["Submissions (Student)"])


async def _read_files(files: list[UploadFile] | None) -> list[tuple[str, bytes, str]]:
    out: list[tuple[str, bytes, str]] = []
    for f in files or []:
        data = await f.read()
        out.append((f.filename or "upload", data, f.content_type or ""))
    return out


# ── Student ──────────────────────────────────────────────────────────────────

@student_router.post("/coursework/{coursework_id}/submit", status_code=201)
async def submit(
    coursework_id: UUID,
    request: Request,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    svc: Annotated[SubmissionService, Depends(get_submission_service)],
    text_answer: Annotated[str | None, Form()] = None,
    files: Annotated[list[UploadFile] | None, File()] = None,
):
    result = await svc.submit(
        UUID(current_user.id), coursework_id, text_answer, await _read_files(files)
    )
    return ok(result.model_dump(), message="Submitted", request_id=request.state.request_id, status_code=201)


@student_router.post("/coursework/{coursework_id}/resubmit")
async def resubmit(
    coursework_id: UUID,
    request: Request,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    svc: Annotated[SubmissionService, Depends(get_submission_service)],
    text_answer: Annotated[str | None, Form()] = None,
    files: Annotated[list[UploadFile] | None, File()] = None,
):
    result = await svc.resubmit(
        UUID(current_user.id), coursework_id, text_answer, await _read_files(files)
    )
    return ok(result.model_dump(), message="Resubmitted", request_id=request.state.request_id)


@student_router.post("/coursework/{coursework_id}/withdraw")
async def withdraw(
    coursework_id: UUID,
    request: Request,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    svc: Annotated[SubmissionService, Depends(get_submission_service)],
):
    await svc.withdraw(UUID(current_user.id), coursework_id)
    return ok({}, message="Submission withdrawn", request_id=request.state.request_id)


@student_router.get("/coursework/{coursework_id}/submission")
async def my_submission(
    coursework_id: UUID,
    request: Request,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    svc: Annotated[SubmissionService, Depends(get_submission_service)],
):
    result = await svc.my_submission(UUID(current_user.id), coursework_id)
    return ok(
        result.model_dump() if result else None, request_id=request.state.request_id
    )


@student_router.get("/classrooms/{classroom_id}/grades")
async def my_grades(
    classroom_id: UUID,
    request: Request,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    svc: Annotated[SubmissionService, Depends(get_submission_service)],
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
):
    result = await svc.my_grades(UUID(current_user.id), classroom_id, page=page, limit=limit)
    return ok(result.model_dump(), request_id=request.state.request_id)


# ── Teacher ──────────────────────────────────────────────────────────────────

@teacher_router.get("/coursework/{coursework_id}/submissions")
async def list_submissions(
    coursework_id: UUID,
    request: Request,
    teacher: Annotated[UserResponse, Depends(require_teacher)],
    svc: Annotated[SubmissionService, Depends(get_submission_service)],
    status: str | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
):
    result = await svc.list_for_coursework(
        UUID(teacher.id), coursework_id, status=status, page=page, limit=limit
    )
    return ok(result.model_dump(), request_id=request.state.request_id)


@teacher_router.get("/submissions/{submission_id}/attachments/{attachment_id}/download")
async def download_submission_attachment(
    submission_id: UUID,
    attachment_id: UUID,
    teacher: Annotated[UserResponse, Depends(require_teacher)],
    svc: Annotated[SubmissionService, Depends(get_submission_service)],
):
    attachment, data = await svc.download_attachment(
        UUID(teacher.id), submission_id, attachment_id
    )
    return Response(
        content=data,
        media_type=attachment.file_type or "application/octet-stream",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(attachment.filename)}",
        },
    )


@teacher_router.post("/submissions/{submission_id}/grade")
async def grade_submission(
    submission_id: UUID,
    body: GradeRequest,
    request: Request,
    teacher: Annotated[UserResponse, Depends(require_teacher)],
    svc: Annotated[SubmissionService, Depends(get_submission_service)],
):
    result = await svc.grade(UUID(teacher.id), submission_id, body)
    return ok(result.model_dump(), message="Graded", request_id=request.state.request_id)


@teacher_router.post("/submissions/{submission_id}/return")
async def return_submission(
    submission_id: UUID,
    request: Request,
    teacher: Annotated[UserResponse, Depends(require_teacher)],
    svc: Annotated[SubmissionService, Depends(get_submission_service)],
):
    result = await svc.return_submission(UUID(teacher.id), submission_id)
    return ok(result.model_dump(), message="Returned to student", request_id=request.state.request_id)
