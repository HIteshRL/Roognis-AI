"""
Classroom discussions — comments on the class stream or a coursework item,
nested replies, emoji reactions, @mentions (with notifications), and search.

Teachers and enrolled students both participate; the service checks the
appropriate membership per call.
"""
from datetime import UTC, datetime
from uuid import UUID

import structlog

from src.application.dtos.discussion import (
    CommentListResponse,
    CommentResponse,
    CreateCommentRequest,
    UpdateCommentRequest,
)
from src.domain.entities.lms import Comment, CommentReaction
from src.domain.exceptions import AuthorizationError, EntityNotFound, ValidationError
from src.domain.repositories.classroom_repository import (
    AbstractClassroomRepository,
    AbstractEnrollmentRepository,
)
from src.domain.repositories.lms_repository import (
    AbstractClassroomTeacherRepository,
    AbstractCommentRepository,
)
from src.domain.repositories.user_repository import AbstractUserRepository

logger = structlog.get_logger(__name__)


class DiscussionService:
    def __init__(
        self,
        comment_repo: AbstractCommentRepository,
        classroom_repo: AbstractClassroomRepository,
        enrollment_repo: AbstractEnrollmentRepository,
        teacher_repo: AbstractClassroomTeacherRepository,
        user_repo: AbstractUserRepository,
        notification_svc=None,
    ) -> None:
        self._comments = comment_repo
        self._classrooms = classroom_repo
        self._enrollments = enrollment_repo
        self._teachers = teacher_repo
        self._users = user_repo
        self._notify = notification_svc

    async def create(
        self, user_id: UUID, classroom_id: UUID, dto: CreateCommentRequest
    ) -> CommentResponse:
        await self._assert_member(user_id, classroom_id)
        parent_id = None
        if dto.parent_id:
            parent = await self._comments.get_by_id(UUID(dto.parent_id))
            if not parent or parent.classroom_id != classroom_id or parent.is_deleted:
                raise EntityNotFound("Parent comment not found")
            parent_id = parent.id

        comment = await self._comments.create(
            Comment(
                classroom_id=classroom_id,
                author_id=user_id,
                body=dto.body,
                coursework_id=UUID(dto.coursework_id) if dto.coursework_id else None,
                parent_id=parent_id,
                mentions=dto.mentions,
            )
        )
        await self._notify_mentions(comment)
        await self._notify_reply(comment, parent_id)
        return await self._to_response(comment)

    async def list(
        self,
        user_id: UUID,
        classroom_id: UUID,
        coursework_id: UUID | None = None,
        parent_id: UUID | None = None,
        search: str | None = None,
        page: int = 1,
        limit: int = 50,
    ) -> CommentListResponse:
        await self._assert_member(user_id, classroom_id)
        items, total = await self._comments.list(
            classroom_id,
            coursework_id=coursework_id,
            parent_id=parent_id,
            search=search,
            page=page,
            limit=limit,
        )
        responses = [await self._to_response(c) for c in items]
        return CommentListResponse(items=responses, total=total, page=page, limit=limit)

    async def update(
        self, user_id: UUID, comment_id: UUID, dto: UpdateCommentRequest
    ) -> CommentResponse:
        comment = await self._get(comment_id)
        if comment.author_id != user_id:
            raise AuthorizationError("You can only edit your own comments")
        comment.body = dto.body
        comment = await self._comments.update(comment)
        return await self._to_response(comment)

    async def delete(self, user_id: UUID, comment_id: UUID) -> None:
        comment = await self._get(comment_id)
        if comment.author_id != user_id and not await self._is_teacher(
            user_id, comment.classroom_id
        ):
            raise AuthorizationError("Only the author or a teacher can delete a comment")
        comment.is_deleted = True
        comment.deleted_at = datetime.now(UTC)
        await self._comments.update(comment)

    async def react(self, user_id: UUID, comment_id: UUID, emoji: str) -> dict[str, int]:
        comment = await self._get(comment_id)
        await self._assert_member(user_id, comment.classroom_id)
        summary = await self._comments.reaction_summary(comment_id)
        try:
            await self._comments.add_reaction(
                CommentReaction(comment_id=comment_id, user_id=user_id, emoji=emoji)
            )
        except Exception:
            raise ValidationError("Already reacted with that emoji") from None
        summary[emoji] = summary.get(emoji, 0) + 1
        return summary

    async def unreact(self, user_id: UUID, comment_id: UUID, emoji: str) -> dict[str, int]:
        await self._comments.remove_reaction(comment_id, user_id, emoji)
        return await self._comments.reaction_summary(comment_id)

    # ── Helpers ──────────────────────────────────────────────────────────────

    async def _notify_mentions(self, comment: Comment) -> None:
        if not self._notify or not comment.mentions:
            return
        author = await self._users.get_by_id(comment.author_id)
        author_name = author.username if author else "Someone"
        targets = []
        for raw in comment.mentions:
            try:
                uid = UUID(str(raw))
            except ValueError:
                continue
            if uid != comment.author_id:
                targets.append(uid)
        if targets:
            await self._notify.emit_many(
                targets,
                type="mention",
                title=f"{author_name} mentioned you",
                body=comment.body[:200],
                data={
                    "classroom_id": str(comment.classroom_id),
                    "comment_id": str(comment.id),
                },
            )

    async def _notify_reply(self, comment: Comment, parent_id: UUID | None) -> None:
        if not self._notify or not parent_id:
            return
        parent = await self._comments.get_by_id(parent_id)
        if parent and parent.author_id != comment.author_id:
            author = await self._users.get_by_id(comment.author_id)
            await self._notify.emit(
                user_id=parent.author_id,
                type="question_answered",
                title=f"{author.username if author else 'Someone'} replied to your comment",
                body=comment.body[:200],
                data={
                    "classroom_id": str(comment.classroom_id),
                    "comment_id": str(comment.id),
                },
            )

    async def _assert_member(self, user_id: UUID, classroom_id: UUID) -> None:
        if await self._enrollments.is_enrolled(classroom_id, user_id):
            return
        if await self._is_teacher(user_id, classroom_id):
            return
        raise AuthorizationError("You are not a member of this classroom")

    async def _is_teacher(self, user_id: UUID, classroom_id: UUID) -> bool:
        classroom = await self._classrooms.get_by_id(classroom_id)
        if not classroom or classroom.is_deleted:
            return False
        if classroom.teacher_id == user_id:
            return True
        return await self._teachers.get(classroom_id, user_id) is not None

    async def _get(self, comment_id: UUID) -> Comment:
        comment = await self._comments.get_by_id(comment_id)
        if not comment or comment.is_deleted:
            raise EntityNotFound("Comment not found")
        return comment

    async def _to_response(self, c: Comment) -> CommentResponse:
        author = await self._users.get_by_id(c.author_id)
        reactions = await self._comments.reaction_summary(c.id)
        _, reply_count = await self._comments.list(
            c.classroom_id, parent_id=c.id, page=1, limit=1
        )
        return CommentResponse(
            id=str(c.id),
            classroom_id=str(c.classroom_id),
            coursework_id=str(c.coursework_id) if c.coursework_id else None,
            parent_id=str(c.parent_id) if c.parent_id else None,
            author_id=str(c.author_id),
            author_name=author.username if author else None,
            body=c.body,
            mentions=c.mentions,
            reactions=reactions,
            reply_count=reply_count,
            created_at=c.created_at.isoformat(),
            updated_at=c.updated_at.isoformat(),
        )
