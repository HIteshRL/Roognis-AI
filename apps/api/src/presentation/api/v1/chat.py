from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Query,
    Request,
    Response,
    UploadFile,
)
from fastapi.responses import StreamingResponse

from src.application.dtos.chat import AttachmentResponse, SendMessageRequest
from src.application.dtos.media import ChapterResponse, MediaJobResponse
from src.application.dtos.user import UserResponse
from src.application.interfaces.dependencies import (
    get_attachment_service,
    get_chat_service,
    get_current_user,
    get_intent_engine,
    get_learning_orchestrator,
    get_user_service,
    get_video_generation_service,
)
from src.application.services.attachment_service import AttachmentService
from src.application.services.chat_service import ChatService
from src.application.services.intent_engine import IntentEngine
from src.application.services.learning_orchestrator import LearningOrchestrator
from src.application.services.user_service import UserService
from src.application.services.video_generation_service import VideoGenerationService
from src.presentation.api.response import ok, paginated

_ATTACHMENT_URL = "/api/v1/chat/attachments"


def _media_job_response(job) -> dict:
    url = (
        f"{_ATTACHMENT_URL}/{job.attachment_id}"
        if job.attachment_id is not None
        else None
    )
    return MediaJobResponse(
        id=str(job.id),
        message_id=str(job.message_id),
        conversation_id=str(job.conversation_id) if job.conversation_id else None,
        kind=job.kind,
        status=job.status,
        progress=job.progress,
        attachment_id=str(job.attachment_id) if job.attachment_id else None,
        url=url,
        error_message=job.error_message,
        created_at=job.created_at.isoformat(),
        updated_at=job.updated_at.isoformat(),
    ).model_dump()

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post("")
async def send_message(
    body: SendMessageRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    chat_svc: Annotated[ChatService, Depends(get_chat_service)],
    user_svc: Annotated[UserService, Depends(get_user_service)],
    orchestrator: Annotated[LearningOrchestrator, Depends(get_learning_orchestrator)],
    intent_engine: Annotated[IntentEngine, Depends(get_intent_engine)],
) -> StreamingResponse:
    user_settings = await user_svc.get_settings(UUID(current_user.id))
    collected_response: list[str] = []
    user_id = UUID(current_user.id)
    question = body.message
    conversation_id = body.conversation_id
    subject = body.subject
    chapter = body.chapter

    current_intent = intent_engine.classify(question)

    async def event_stream():
        async for chunk in chat_svc.stream_response(
            user_id=user_id,
            dto=body,
            llm_model=user_settings.llm_model,
            temperature=user_settings.temperature,
            current_intent=current_intent,
        ):
            collected_response.append(chunk)
            yield chunk

    async def run_learning_pipeline():
        ai_text = "".join(collected_response)
        # Follow-up turns omit subject/chapter (only new conversations send
        # them), so fall back to the conversation's persisted scope — otherwise
        # sessions/mastery/gaps get recorded with no subject/chapter.
        pipe_subject, pipe_chapter = subject, chapter
        if conversation_id and (pipe_subject is None or pipe_chapter is None):
            stored_subject, stored_chapter = await chat_svc.get_conversation_scope(
                user_id, conversation_id
            )
            pipe_subject = pipe_subject or stored_subject
            pipe_chapter = pipe_chapter or stored_chapter
        await orchestrator.process(
            user_id=user_id,
            question=question,
            ai_response=ai_text,
            conversation_id=conversation_id,
            subject=pipe_subject,
            chapter=pipe_chapter,
            intent=current_intent,
        )

    background_tasks.add_task(run_learning_pipeline)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "X-Request-ID": request.state.request_id,
        },
    )


@router.post("/attachments", status_code=201)
async def upload_attachment(
    request: Request,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    attachment_svc: Annotated[AttachmentService, Depends(get_attachment_service)],
    file: Annotated[UploadFile, File()],
):
    file_bytes = await file.read()
    attachment = await attachment_svc.upload_image(
        user_id=UUID(current_user.id),
        filename=file.filename or "image",
        file_bytes=file_bytes,
        content_type=file.content_type or "",
    )
    return ok(
        AttachmentResponse(
            id=str(attachment.id),
            kind=attachment.kind,
            content_type=attachment.content_type,
            file_size=attachment.file_size,
            url=f"/api/v1/chat/attachments/{attachment.id}",
            created_at=attachment.created_at.isoformat(),
        ).model_dump(),
        message="Attachment uploaded",
        request_id=request.state.request_id,
    )


@router.get("/attachments/{attachment_id}")
async def get_attachment(
    attachment_id: UUID,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    attachment_svc: Annotated[AttachmentService, Depends(get_attachment_service)],
):
    attachment = await attachment_svc.get_owned(attachment_id, UUID(current_user.id))
    data = await attachment_svc.read_bytes(attachment)
    return Response(
        content=data,
        media_type=attachment.content_type,
        headers={"Cache-Control": "private, max-age=86400"},
    )


@router.post("/messages/{message_id}/video", status_code=202)
async def generate_message_video(
    message_id: UUID,
    request: Request,
    background_tasks: BackgroundTasks,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    video_svc: Annotated[
        VideoGenerationService, Depends(get_video_generation_service)
    ],
):
    job = await video_svc.request(UUID(current_user.id), message_id)
    background_tasks.add_task(video_svc.run, job.id)
    return ok(
        _media_job_response(job),
        message="Video generation started",
        request_id=request.state.request_id,
    )


@router.get("/media-jobs/{job_id}")
async def get_media_job(
    job_id: UUID,
    request: Request,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    video_svc: Annotated[
        VideoGenerationService, Depends(get_video_generation_service)
    ],
):
    job = await video_svc.get_job(job_id, UUID(current_user.id))
    return ok(_media_job_response(job), request_id=request.state.request_id)


@router.get("/subjects")
async def list_subjects(
    request: Request,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    chat_svc: Annotated[ChatService, Depends(get_chat_service)],
):
    counts = await chat_svc.get_subject_counts(UUID(current_user.id))
    return ok(
        [c.model_dump() for c in counts],
        request_id=request.state.request_id,
    )


@router.get("/subjects/{subject}/chapters")
async def list_chapters(
    subject: str,
    request: Request,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    chat_svc: Annotated[ChatService, Depends(get_chat_service)],
):
    chapters = await chat_svc.get_chapters(UUID(current_user.id), subject)
    return ok(
        [
            ChapterResponse(chapter=chapter, conversation_count=count).model_dump()
            for chapter, count in chapters
        ],
        request_id=request.state.request_id,
    )


@router.get("/history")
async def list_conversations(
    request: Request,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    chat_svc: Annotated[ChatService, Depends(get_chat_service)],
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    subject: str | None = Query(default=None),
    chapter: str | None = Query(default=None),
):
    conversations, total = await chat_svc.list_conversations(
        UUID(current_user.id), page, limit, subject=subject, chapter=chapter,
    )
    return paginated(
        data=[c.model_dump() for c in conversations],
        total=total,
        page=page,
        limit=limit,
        request_id=request.state.request_id,
    )


@router.get("/history/{conversation_id}")
async def get_conversation(
    conversation_id: UUID,
    request: Request,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    chat_svc: Annotated[ChatService, Depends(get_chat_service)],
):
    result = await chat_svc.get_conversation(UUID(current_user.id), conversation_id)
    return ok(result.model_dump(), request_id=request.state.request_id)


@router.delete("/history/{conversation_id}", status_code=200)
async def delete_conversation(
    conversation_id: UUID,
    request: Request,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    chat_svc: Annotated[ChatService, Depends(get_chat_service)],
):
    await chat_svc.delete_conversation(UUID(current_user.id), conversation_id)
    return ok({}, message="Conversation deleted", request_id=request.state.request_id)
