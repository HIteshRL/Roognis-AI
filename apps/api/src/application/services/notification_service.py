"""
In-app notification center for both portals.

Emission is fail-open (same principle as the learning pipeline): a failed
notification must never break the request that triggered it. Reading/marking
is fail-closed like any normal endpoint.
"""
from uuid import UUID

import structlog

from src.application.dtos.notification import NotificationListResponse, NotificationResponse
from src.domain.entities.lms import Notification
from src.domain.repositories.lms_repository import AbstractNotificationRepository

logger = structlog.get_logger(__name__)


class NotificationService:
    def __init__(self, notification_repo: AbstractNotificationRepository) -> None:
        self._notifications = notification_repo

    # ── Emission (fail-open) ─────────────────────────────────────────────────

    async def emit(
        self,
        user_id: UUID,
        type: str,
        title: str,
        body: str = "",
        data: dict | None = None,
    ) -> None:
        try:
            await self._notifications.create(
                Notification(user_id=user_id, type=type, title=title, body=body, data=data or {})
            )
        except Exception as exc:
            logger.warning("notification_emit_failed", type=type, error=str(exc))

    async def emit_many(
        self,
        user_ids: list[UUID],
        type: str,
        title: str,
        body: str = "",
        data: dict | None = None,
    ) -> None:
        try:
            await self._notifications.create_many(
                [
                    Notification(
                        user_id=uid, type=type, title=title, body=body, data=data or {}
                    )
                    for uid in user_ids
                ]
            )
        except Exception as exc:
            logger.warning("notification_emit_many_failed", type=type, error=str(exc))

    # ── Reading ──────────────────────────────────────────────────────────────

    async def list_for_user(
        self, user_id: UUID, unread_only: bool = False, page: int = 1, limit: int = 20
    ) -> NotificationListResponse:
        items, total = await self._notifications.list_for_user(
            user_id, unread_only=unread_only, page=page, limit=limit
        )
        unread = await self._notifications.unread_count(user_id)
        return NotificationListResponse(
            items=[self._to_response(n) for n in items],
            total=total,
            unread_count=unread,
            page=page,
            limit=limit,
        )

    async def unread_count(self, user_id: UUID) -> int:
        return await self._notifications.unread_count(user_id)

    async def mark_read(self, user_id: UUID, notification_id: UUID) -> None:
        await self._notifications.mark_read(notification_id, user_id)

    async def mark_all_read(self, user_id: UUID) -> None:
        await self._notifications.mark_all_read(user_id)

    @staticmethod
    def _to_response(n: Notification) -> NotificationResponse:
        return NotificationResponse(
            id=str(n.id),
            type=n.type,
            title=n.title,
            body=n.body,
            data=n.data,
            is_read=n.is_read,
            created_at=n.created_at.isoformat(),
        )
