"""Discussion endpoints — shared by teachers and students in a classroom."""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request

from src.application.dtos.discussion import (
    CreateCommentRequest,
    ReactionRequest,
    UpdateCommentRequest,
)
from src.application.dtos.user import UserResponse
from src.application.interfaces.dependencies import (
    get_current_user,
    get_discussion_service,
)
from src.application.services.discussion_service import DiscussionService
from src.presentation.api.response import ok

router = APIRouter(prefix="/classrooms", tags=["Discussions"])


@router.post("/{classroom_id}/comments", status_code=201)
async def create_comment(
    classroom_id: UUID,
    body: CreateCommentRequest,
    request: Request,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    svc: Annotated[DiscussionService, Depends(get_discussion_service)],
):
    result = await svc.create(UUID(current_user.id), classroom_id, body)
    return ok(result.model_dump(), message="Comment posted", request_id=request.state.request_id, status_code=201)


@router.get("/{classroom_id}/comments")
async def list_comments(
    classroom_id: UUID,
    request: Request,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    svc: Annotated[DiscussionService, Depends(get_discussion_service)],
    coursework_id: UUID | None = None,
    parent_id: UUID | None = None,
    search: str | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
):
    result = await svc.list(
        UUID(current_user.id), classroom_id,
        coursework_id=coursework_id, parent_id=parent_id, search=search,
        page=page, limit=limit,
    )
    return ok(result.model_dump(), request_id=request.state.request_id)


@router.patch("/comments/{comment_id}")
async def update_comment(
    comment_id: UUID,
    body: UpdateCommentRequest,
    request: Request,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    svc: Annotated[DiscussionService, Depends(get_discussion_service)],
):
    result = await svc.update(UUID(current_user.id), comment_id, body)
    return ok(result.model_dump(), message="Comment updated", request_id=request.state.request_id)


@router.delete("/comments/{comment_id}")
async def delete_comment(
    comment_id: UUID,
    request: Request,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    svc: Annotated[DiscussionService, Depends(get_discussion_service)],
):
    await svc.delete(UUID(current_user.id), comment_id)
    return ok({}, message="Comment deleted", request_id=request.state.request_id)


@router.post("/comments/{comment_id}/reactions")
async def add_reaction(
    comment_id: UUID,
    body: ReactionRequest,
    request: Request,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    svc: Annotated[DiscussionService, Depends(get_discussion_service)],
):
    reactions = await svc.react(UUID(current_user.id), comment_id, body.emoji)
    return ok({"reactions": reactions}, request_id=request.state.request_id)


@router.delete("/comments/{comment_id}/reactions/{emoji}")
async def remove_reaction(
    comment_id: UUID,
    emoji: str,
    request: Request,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    svc: Annotated[DiscussionService, Depends(get_discussion_service)],
):
    reactions = await svc.unreact(UUID(current_user.id), comment_id, emoji)
    return ok({"reactions": reactions}, request_id=request.state.request_id)
