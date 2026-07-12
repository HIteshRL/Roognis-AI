"""
/teacher — teacher persona (Google Classroom model).

Teachers create classrooms ("subjects"), add ordered chapters, share a join
code, manage enrolled students, and upload content into a chapter. Content
upload reuses the existing document ingestion pipeline (chunk → OCR → embed →
index), scoped to the chapter's KnowledgeBase.
"""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Request, UploadFile

from src.application.dtos.classroom import (
    CreateChapterRequest,
    CreateClassroomRequest,
    InviteRequest,
    UpdateChapterRequest,
    UpdateClassroomRequest,
)
from src.application.dtos.knowledge import DocumentUploadResponse
from src.application.dtos.user import UserResponse
from src.application.interfaces.dependencies import (
    get_classroom_service,
    get_document_service,
    get_settings,
    get_vision_ocr_service,
    require_teacher,
)
from src.application.services.classroom_service import ClassroomService
from src.application.services.document_service import DocumentService
from src.application.services.ingestion_pipeline import IngestionPipeline
from src.config import Settings
from src.domain.exceptions import EntityNotFound
from src.infrastructure.embeddings.factory import get_embedding_provider
from src.infrastructure.vector.factory import get_vector_store
from src.presentation.api.response import ok

router = APIRouter(prefix="/teacher", tags=["Teacher"])


def _make_pipeline(settings: Settings) -> IngestionPipeline:
    return IngestionPipeline(
        vector_store=get_vector_store(),
        embedding_provider=get_embedding_provider(),
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        chunk_strategy=settings.chunk_strategy,
        vision_ocr_svc=get_vision_ocr_service(settings),
    )


# ── Classrooms ───────────────────────────────────────────────────────────────

@router.post("/classrooms", status_code=201)
async def create_classroom(
    body: CreateClassroomRequest,
    request: Request,
    teacher: Annotated[UserResponse, Depends(require_teacher)],
    svc: Annotated[ClassroomService, Depends(get_classroom_service)],
):
    result = await svc.create_classroom(UUID(teacher.id), body)
    return ok(result.model_dump(), message="Classroom created", request_id=request.state.request_id, status_code=201)


@router.get("/classrooms")
async def list_classrooms(
    request: Request,
    teacher: Annotated[UserResponse, Depends(require_teacher)],
    svc: Annotated[ClassroomService, Depends(get_classroom_service)],
):
    result = await svc.list_teacher_classrooms(UUID(teacher.id))
    return ok([r.model_dump() for r in result], request_id=request.state.request_id)


@router.get("/classrooms/{classroom_id}")
async def get_classroom(
    classroom_id: UUID,
    request: Request,
    teacher: Annotated[UserResponse, Depends(require_teacher)],
    svc: Annotated[ClassroomService, Depends(get_classroom_service)],
):
    result = await svc.get_classroom_for_teacher(UUID(teacher.id), classroom_id)
    return ok(result.model_dump(), request_id=request.state.request_id)


@router.patch("/classrooms/{classroom_id}")
async def update_classroom(
    classroom_id: UUID,
    body: UpdateClassroomRequest,
    request: Request,
    teacher: Annotated[UserResponse, Depends(require_teacher)],
    svc: Annotated[ClassroomService, Depends(get_classroom_service)],
):
    result = await svc.update_classroom(UUID(teacher.id), classroom_id, body)
    return ok(result.model_dump(), message="Classroom updated", request_id=request.state.request_id)


@router.post("/classrooms/{classroom_id}/archive")
async def archive_classroom(
    classroom_id: UUID,
    request: Request,
    teacher: Annotated[UserResponse, Depends(require_teacher)],
    svc: Annotated[ClassroomService, Depends(get_classroom_service)],
):
    await svc.archive_classroom(UUID(teacher.id), classroom_id)
    return ok({}, message="Classroom archived", request_id=request.state.request_id)


@router.post("/classrooms/{classroom_id}/regenerate-code")
async def regenerate_code(
    classroom_id: UUID,
    request: Request,
    teacher: Annotated[UserResponse, Depends(require_teacher)],
    svc: Annotated[ClassroomService, Depends(get_classroom_service)],
):
    result = await svc.regenerate_join_code(UUID(teacher.id), classroom_id)
    return ok(result.model_dump(), message="Join code regenerated", request_id=request.state.request_id)


@router.delete("/classrooms/{classroom_id}")
async def delete_classroom(
    classroom_id: UUID,
    request: Request,
    teacher: Annotated[UserResponse, Depends(require_teacher)],
    svc: Annotated[ClassroomService, Depends(get_classroom_service)],
):
    await svc.delete_classroom(UUID(teacher.id), classroom_id)
    return ok({}, message="Classroom deleted", request_id=request.state.request_id)


@router.post("/classrooms/{classroom_id}/join-code/enable")
async def enable_join_code(
    classroom_id: UUID,
    request: Request,
    teacher: Annotated[UserResponse, Depends(require_teacher)],
    svc: Annotated[ClassroomService, Depends(get_classroom_service)],
):
    result = await svc.set_join_code_enabled(UUID(teacher.id), classroom_id, True)
    return ok(result.model_dump(), message="Join code enabled", request_id=request.state.request_id)


@router.post("/classrooms/{classroom_id}/join-code/disable")
async def disable_join_code(
    classroom_id: UUID,
    request: Request,
    teacher: Annotated[UserResponse, Depends(require_teacher)],
    svc: Annotated[ClassroomService, Depends(get_classroom_service)],
):
    result = await svc.set_join_code_enabled(UUID(teacher.id), classroom_id, False)
    return ok(result.model_dump(), message="Join code disabled", request_id=request.state.request_id)


# ── Invitations & co-teachers ────────────────────────────────────────────────

@router.post("/classrooms/{classroom_id}/invitations", status_code=201)
async def invite_member(
    classroom_id: UUID,
    body: InviteRequest,
    request: Request,
    teacher: Annotated[UserResponse, Depends(require_teacher)],
    svc: Annotated[ClassroomService, Depends(get_classroom_service)],
):
    result = await svc.invite(UUID(teacher.id), classroom_id, body.email, body.role)
    return ok(result.model_dump(), message="Invitation sent", request_id=request.state.request_id, status_code=201)


@router.get("/classrooms/{classroom_id}/invitations")
async def list_invitations(
    classroom_id: UUID,
    request: Request,
    teacher: Annotated[UserResponse, Depends(require_teacher)],
    svc: Annotated[ClassroomService, Depends(get_classroom_service)],
    status: str | None = None,
):
    result = await svc.list_invitations(UUID(teacher.id), classroom_id, status=status)
    return ok([r.model_dump() for r in result], request_id=request.state.request_id)


@router.delete("/invitations/{invitation_id}")
async def revoke_invitation(
    invitation_id: UUID,
    request: Request,
    teacher: Annotated[UserResponse, Depends(require_teacher)],
    svc: Annotated[ClassroomService, Depends(get_classroom_service)],
):
    await svc.revoke_invitation(UUID(teacher.id), invitation_id)
    return ok({}, message="Invitation revoked", request_id=request.state.request_id)


@router.get("/classrooms/{classroom_id}/co-teachers")
async def list_co_teachers(
    classroom_id: UUID,
    request: Request,
    teacher: Annotated[UserResponse, Depends(require_teacher)],
    svc: Annotated[ClassroomService, Depends(get_classroom_service)],
):
    result = await svc.list_co_teachers(UUID(teacher.id), classroom_id)
    return ok([r.model_dump() for r in result], request_id=request.state.request_id)


@router.delete("/classrooms/{classroom_id}/co-teachers/{co_teacher_id}")
async def remove_co_teacher(
    classroom_id: UUID,
    co_teacher_id: UUID,
    request: Request,
    teacher: Annotated[UserResponse, Depends(require_teacher)],
    svc: Annotated[ClassroomService, Depends(get_classroom_service)],
):
    await svc.remove_co_teacher(UUID(teacher.id), classroom_id, co_teacher_id)
    return ok({}, message="Co-teacher removed", request_id=request.state.request_id)


# ── Join requests (approval flow) ────────────────────────────────────────────

@router.get("/classrooms/{classroom_id}/join-requests")
async def list_join_requests(
    classroom_id: UUID,
    request: Request,
    teacher: Annotated[UserResponse, Depends(require_teacher)],
    svc: Annotated[ClassroomService, Depends(get_classroom_service)],
):
    result = await svc.list_pending_enrollments(UUID(teacher.id), classroom_id)
    return ok([r.model_dump() for r in result], request_id=request.state.request_id)


@router.post("/classrooms/{classroom_id}/join-requests/{student_id}/approve")
async def approve_join_request(
    classroom_id: UUID,
    student_id: UUID,
    request: Request,
    teacher: Annotated[UserResponse, Depends(require_teacher)],
    svc: Annotated[ClassroomService, Depends(get_classroom_service)],
):
    await svc.approve_enrollment(UUID(teacher.id), classroom_id, student_id)
    return ok({}, message="Request approved", request_id=request.state.request_id)


@router.post("/classrooms/{classroom_id}/join-requests/{student_id}/reject")
async def reject_join_request(
    classroom_id: UUID,
    student_id: UUID,
    request: Request,
    teacher: Annotated[UserResponse, Depends(require_teacher)],
    svc: Annotated[ClassroomService, Depends(get_classroom_service)],
):
    await svc.reject_enrollment(UUID(teacher.id), classroom_id, student_id)
    return ok({}, message="Request rejected", request_id=request.state.request_id)


# ── Students ─────────────────────────────────────────────────────────────────

@router.get("/classrooms/{classroom_id}/students")
async def list_students(
    classroom_id: UUID,
    request: Request,
    teacher: Annotated[UserResponse, Depends(require_teacher)],
    svc: Annotated[ClassroomService, Depends(get_classroom_service)],
):
    result = await svc.list_students(UUID(teacher.id), classroom_id)
    return ok([r.model_dump() for r in result], request_id=request.state.request_id)


@router.delete("/classrooms/{classroom_id}/students/{student_id}")
async def remove_student(
    classroom_id: UUID,
    student_id: UUID,
    request: Request,
    teacher: Annotated[UserResponse, Depends(require_teacher)],
    svc: Annotated[ClassroomService, Depends(get_classroom_service)],
):
    await svc.remove_student(UUID(teacher.id), classroom_id, student_id)
    return ok({}, message="Student removed", request_id=request.state.request_id)


# ── Chapters ─────────────────────────────────────────────────────────────────

@router.post("/classrooms/{classroom_id}/chapters", status_code=201)
async def add_chapter(
    classroom_id: UUID,
    body: CreateChapterRequest,
    request: Request,
    teacher: Annotated[UserResponse, Depends(require_teacher)],
    svc: Annotated[ClassroomService, Depends(get_classroom_service)],
):
    result = await svc.add_chapter(UUID(teacher.id), classroom_id, body)
    return ok(result.model_dump(), message="Chapter added", request_id=request.state.request_id, status_code=201)


@router.get("/classrooms/{classroom_id}/chapters")
async def list_chapters(
    classroom_id: UUID,
    request: Request,
    teacher: Annotated[UserResponse, Depends(require_teacher)],
    svc: Annotated[ClassroomService, Depends(get_classroom_service)],
):
    # Ownership is enforced when the classroom is fetched for the teacher.
    await svc.get_classroom_for_teacher(UUID(teacher.id), classroom_id)
    result = await svc.list_chapters(classroom_id)
    return ok([r.model_dump() for r in result], request_id=request.state.request_id)


@router.patch("/chapters/{chapter_id}")
async def update_chapter(
    chapter_id: UUID,
    body: UpdateChapterRequest,
    request: Request,
    teacher: Annotated[UserResponse, Depends(require_teacher)],
    svc: Annotated[ClassroomService, Depends(get_classroom_service)],
):
    result = await svc.update_chapter(UUID(teacher.id), chapter_id, body)
    return ok(result.model_dump(), message="Chapter updated", request_id=request.state.request_id)


@router.delete("/chapters/{chapter_id}")
async def delete_chapter(
    chapter_id: UUID,
    request: Request,
    teacher: Annotated[UserResponse, Depends(require_teacher)],
    svc: Annotated[ClassroomService, Depends(get_classroom_service)],
):
    await svc.delete_chapter(UUID(teacher.id), chapter_id)
    return ok({}, message="Chapter deleted", request_id=request.state.request_id)


# ── Chapter content upload (reuses the ingestion pipeline) ───────────────────

@router.post("/chapters/{chapter_id}/content", status_code=201)
async def upload_chapter_content(
    chapter_id: UUID,
    request: Request,
    background_tasks: BackgroundTasks,
    teacher: Annotated[UserResponse, Depends(require_teacher)],
    svc: Annotated[ClassroomService, Depends(get_classroom_service)],
    doc_svc: Annotated[DocumentService, Depends(get_document_service)],
    settings: Annotated[Settings, Depends(get_settings)],
    file: Annotated[UploadFile, File()],
    title: Annotated[str | None, Form()] = None,
    description: Annotated[str | None, Form()] = None,
):
    kb_id = await svc.get_chapter_kb_for_teacher(UUID(teacher.id), chapter_id)
    if not kb_id:
        raise EntityNotFound("Chapter has no content store")

    file_bytes = await file.read()
    doc, job = await doc_svc.upload(
        kb_id=kb_id,
        user_id=UUID(teacher.id),
        filename=file.filename or "upload",
        file_bytes=file_bytes,
        content_type=file.content_type or "",
        title=title,
        description=description,
    )

    pipeline = _make_pipeline(settings)
    background_tasks.add_task(pipeline.run, doc.id, doc.storage_path, doc.file_type)

    return ok(
        DocumentUploadResponse(
            id=str(doc.id),
            knowledge_base_id=str(doc.knowledge_base_id),
            filename=doc.filename,
            file_type=doc.file_type,
            file_size=doc.file_size,
            status=doc.status,
            job_id=str(job.id),
            created_at=doc.created_at.isoformat(),
        ).model_dump(),
        message="Content uploaded. Ingestion started.",
        request_id=request.state.request_id,
        status_code=201,
    )
