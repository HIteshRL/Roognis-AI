"""
/rag — Curriculum-bound RAG endpoints.

All query endpoints enforce strict academic hierarchy filtering.
The LLM answers ONLY from retrieved curriculum context.
"""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Query, Request, UploadFile

from src.application.dtos.knowledge import (
    CurriculumFilter,
    DocumentUploadResponse,
    IngestionJobResponse,
    RagQueryRequest,
    RagQueryResponse,
)
from src.application.dtos.user import UserResponse
from src.application.interfaces.dependencies import (
    get_current_user,
    get_document_service,
    get_rag_service,
    get_settings,
    get_vision_ocr_service,
    require_admin,
)
from src.application.services.document_service import DocumentService
from src.application.services.ingestion_pipeline import IngestionPipeline
from src.application.services.rag_service import RagService
from src.config import Settings
from src.infrastructure.embeddings.factory import get_embedding_provider
from src.infrastructure.vector.factory import get_vector_store
from src.presentation.api.response import ok

router = APIRouter(prefix="/rag", tags=["RAG"])


def _make_pipeline(settings: Settings) -> IngestionPipeline:
    return IngestionPipeline(
        vector_store=get_vector_store(),
        embedding_provider=get_embedding_provider(),
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        chunk_strategy=settings.chunk_strategy,
        vision_ocr_svc=get_vision_ocr_service(settings),
    )


# ── POST /rag/upload ──────────────────────────────────────────────────────────

@router.post("/upload", status_code=201)
async def rag_upload(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    knowledge_base_id: str = Form(...),
    title: str | None = Form(default=None),
    description: str | None = Form(default=None),
    admin: UserResponse = Depends(require_admin),
    svc: DocumentService = Depends(get_document_service),
    settings: Settings = Depends(get_settings),
):
    """Upload a document into a knowledge base. Ingestion starts immediately."""
    file_bytes = await file.read()
    doc, job = await svc.upload(
        kb_id=UUID(knowledge_base_id),
        user_id=UUID(admin.id),
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
        message="Document uploaded. Curriculum ingestion started.",
        request_id=request.state.request_id,
        status_code=201,
    )


# ── POST /rag/index ───────────────────────────────────────────────────────────

@router.post("/index/{document_id}", status_code=202)
async def rag_index(
    document_id: UUID,
    request: Request,
    background_tasks: BackgroundTasks,
    _: UserResponse = Depends(require_admin),
    svc: DocumentService = Depends(get_document_service),
    settings: Settings = Depends(get_settings),
):
    """(Re)index a document — useful when chunking config or embeddings change."""
    doc = await svc.get_document(document_id)
    pipeline = _make_pipeline(settings)
    background_tasks.add_task(pipeline.run, doc.id, doc.storage_path, doc.file_type)
    return ok({}, message="Indexing started", request_id=request.state.request_id)


# ── POST /rag/query ───────────────────────────────────────────────────────────

@router.post("/query")
async def rag_query(
    body: RagQueryRequest,
    request: Request,
    _: UserResponse = Depends(get_current_user),
    rag_svc: RagService = Depends(get_rag_service),
):
    """
    Curriculum-filtered RAG query.

    Provide curriculum filters to constrain retrieval to a specific
    institution / grade / subject / chapter scope.  The LLM will only answer
    from retrieved context; if nothing matches it responds with the
    "I cannot find this information in the provided curriculum." message.
    """
    result = await rag_svc.query(body)
    return ok(result.model_dump(), request_id=request.state.request_id)


# ── GET /rag/status ───────────────────────────────────────────────────────────

@router.get("/status/{document_id}")
async def rag_status(
    document_id: UUID,
    request: Request,
    _: UserResponse = Depends(get_current_user),
    svc: DocumentService = Depends(get_document_service),
):
    """Poll the ingestion job status for a document."""
    job = await svc.get_job_status(document_id)
    return ok(job.model_dump(), request_id=request.state.request_id)


# ── DELETE /rag/document/:id ──────────────────────────────────────────────────

@router.delete("/document/{document_id}")
async def rag_delete_document(
    document_id: UUID,
    request: Request,
    admin: UserResponse = Depends(require_admin),
    svc: DocumentService = Depends(get_document_service),
):
    """Delete a document and all its chunks and vectors."""
    await svc.delete_document(document_id, UUID(admin.id))
    return ok({}, message="Document deleted from curriculum", request_id=request.state.request_id)
