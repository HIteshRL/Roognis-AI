from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse

from src.application.dtos.chat import SendMessageRequest
from src.application.dtos.user import UserResponse
from src.application.interfaces.dependencies import (
    get_chat_service,
    get_current_user,
    get_user_service,
)
from src.application.services.chat_service import ChatService
from src.application.services.user_service import UserService
from src.presentation.api.response import ok, paginated

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post("")
async def send_message(
    body: SendMessageRequest,
    request: Request,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    chat_svc: Annotated[ChatService, Depends(get_chat_service)],
    user_svc: Annotated[UserService, Depends(get_user_service)],
) -> StreamingResponse:
    user_settings = await user_svc.get_settings(UUID(current_user.id))

    async def event_stream():
        async for chunk in chat_svc.stream_response(
            user_id=UUID(current_user.id),
            dto=body,
            llm_model=user_settings.llm_model,
            temperature=user_settings.temperature,
        ):
            yield chunk

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "X-Request-ID": request.state.request_id,
        },
    )


@router.get("/history")
async def list_conversations(
    request: Request,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    chat_svc: Annotated[ChatService, Depends(get_chat_service)],
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
):
    conversations, total = await chat_svc.list_conversations(
        UUID(current_user.id), page, limit
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
