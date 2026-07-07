from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, File, Query, Request, UploadFile

from src.application.dtos.knowledge import (
    DocumentUploadResponse,
)
from src.application.dtos.user import UserResponse
from src.application.interfaces.dependencies import (
    get_current_user,
    get_document_service,
    get_settings,
    require_admin,
)
from src.application.services.document_service import DocumentService
from src.application.services.ingestion_pipeline import IngestionPipeline
from src.config import Settings
from src.infrastructure.embeddings.factory import get_embedding_provider
from src.infrastructure.vector.factory import get_vector_store
from src.presentation.api.response import ok, paginated

router = APIRouter(prefix="/documents", tags=["Documents"])


def _make_pipeline(settings: Settings) -> IngestionPipeline:
    return IngestionPipeline(
        vector_store=get_vector_store(),
        embedding_provider=get_embedding_provider(),
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        chunk_strategy=settings.chunk_strategy,
        chunk_target_tokens=settings.chunk_target_tokens,
        chunk_min_tokens=settings.chunk_min_tokens,
        chunk_safety_ratio=settings.chunk_safety_ratio,
        chunk_semantic_threshold=settings.chunk_semantic_threshold,
        chunk_semantic_enabled=settings.chunk_semantic_enabled,
    )


@router.post("/upload/{kb_id}", status_code=201)
async def upload_document(
    kb_id: UUID,
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    admin: UserResponse = Depends(require_admin),
    svc: DocumentService = Depends(get_document_service),
    settings: Settings = Depends(get_settings),
):
    file_bytes = await file.read()
    doc, job = await svc.upload(
        kb_id=kb_id,
        user_id=UUID(admin.id),
        filename=file.filename or "upload",
        file_bytes=file_bytes,
        content_type=file.content_type or "",
    )

    pipeline = _make_pipeline(settings)
    background_tasks.add_task(
        pipeline.run, doc.id, doc.storage_path, doc.file_type
    )

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
        message="Document uploaded. Processing started.",
        request_id=request.state.request_id,
        status_code=201,
    )


@router.get("/{kb_id}")
async def list_documents(
    kb_id: UUID,
    request: Request,
    _: UserResponse = Depends(get_current_user),
    svc: DocumentService = Depends(get_document_service),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
):
    docs, total = await svc.list_documents(kb_id, page, limit)
    return paginated(
        data=[svc._to_response(d).model_dump() for d in docs],
        total=total,
        page=page,
        limit=limit,
        request_id=request.state.request_id,
    )


@router.get("/{kb_id}/{document_id}")
async def get_document(
    kb_id: UUID,
    document_id: UUID,
    request: Request,
    _: UserResponse = Depends(get_current_user),
    svc: DocumentService = Depends(get_document_service),
):
    doc = await svc.get_document(document_id)
    return ok(svc._to_response(doc).model_dump(), request_id=request.state.request_id)


@router.delete("/{kb_id}/{document_id}")
async def delete_document(
    kb_id: UUID,
    document_id: UUID,
    request: Request,
    admin: UserResponse = Depends(require_admin),
    svc: DocumentService = Depends(get_document_service),
):
    await svc.delete_document(document_id, UUID(admin.id))
    return ok({}, message="Document deleted", request_id=request.state.request_id)


@router.get("/{kb_id}/{document_id}/chunks")
async def get_chunks(
    kb_id: UUID,
    document_id: UUID,
    request: Request,
    _: UserResponse = Depends(get_current_user),
    svc: DocumentService = Depends(get_document_service),
):
    chunks = await svc.get_chunks(document_id)
    return ok([c.model_dump() for c in chunks], request_id=request.state.request_id)


@router.get("/{kb_id}/{document_id}/status")
async def ingestion_status(
    kb_id: UUID,
    document_id: UUID,
    request: Request,
    _: UserResponse = Depends(get_current_user),
    svc: DocumentService = Depends(get_document_service),
):
    job = await svc.get_job_status(document_id)
    return ok(job.model_dump(), request_id=request.state.request_id)


@router.post("/{kb_id}/{document_id}/reindex", status_code=202)
async def reindex_document(
    kb_id: UUID,
    document_id: UUID,
    request: Request,
    background_tasks: BackgroundTasks,
    _: UserResponse = Depends(require_admin),
    svc: DocumentService = Depends(get_document_service),
    settings: Settings = Depends(get_settings),
):
    doc = await svc.get_document(document_id)
    pipeline = _make_pipeline(settings)
    background_tasks.add_task(
        pipeline.run, doc.id, doc.storage_path, doc.file_type
    )
    return ok({}, message="Reindexing started", request_id=request.state.request_id)
