import base64
from uuid import UUID, uuid4

import structlog

from src.domain.entities.attachment import MessageAttachment
from src.domain.exceptions import AuthorizationError, EntityNotFound, ValidationError
from src.domain.repositories.attachment_repository import (
    AbstractMessageAttachmentRepository,
)
from src.infrastructure.storage.base import AbstractFileStorage

logger = structlog.get_logger(__name__)

_EXT_BY_TYPE = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "image/gif": "gif",
}


class AttachmentService:
    def __init__(
        self,
        attachment_repo: AbstractMessageAttachmentRepository,
        storage: AbstractFileStorage,
        allowed_image_types: list[str],
        max_image_size_bytes: int,
    ) -> None:
        self._attachments = attachment_repo
        self._storage = storage
        self._allowed_types = set(allowed_image_types)
        self._max_size = max_image_size_bytes

    async def upload_image(
        self,
        user_id: UUID,
        filename: str,
        file_bytes: bytes,
        content_type: str,
    ) -> MessageAttachment:
        content_type = (content_type or "").split(";")[0].strip().lower()
        if content_type not in self._allowed_types:
            raise ValidationError(
                f"Unsupported image type '{content_type}'. "
                f"Allowed: {', '.join(sorted(self._allowed_types))}"
            )
        if not file_bytes:
            raise ValidationError("Empty file")
        if len(file_bytes) > self._max_size:
            raise ValidationError(
                f"Image exceeds max size of {self._max_size // (1024 * 1024)}MB"
            )

        attachment_id = uuid4()
        ext = _EXT_BY_TYPE.get(content_type, "bin")
        destination = f"chat/{user_id}/{attachment_id}.{ext}"
        storage_path = await self._storage.save(file_bytes, destination)

        attachment = MessageAttachment(
            id=attachment_id,
            user_id=user_id,
            storage_path=storage_path,
            content_type=content_type,
            file_size=len(file_bytes),
            kind="image",
        )
        saved = await self._attachments.create(attachment)
        logger.info(
            "attachment_uploaded",
            attachment_id=str(saved.id),
            user_id=str(user_id),
            size=saved.file_size,
        )
        return saved

    async def get_owned(
        self, attachment_id: UUID, user_id: UUID
    ) -> MessageAttachment:
        attachment = await self._attachments.get_by_id(attachment_id)
        if not attachment:
            raise EntityNotFound("Attachment not found")
        if attachment.user_id != user_id:
            raise AuthorizationError("Access denied")
        return attachment

    async def read_bytes(self, attachment: MessageAttachment) -> bytes:
        return await self._storage.read(attachment.storage_path)

    async def to_data_url(self, attachment: MessageAttachment) -> str:
        raw = await self._storage.read(attachment.storage_path)
        encoded = base64.b64encode(raw).decode("ascii")
        return f"data:{attachment.content_type};base64,{encoded}"

    async def data_urls_for(
        self, attachment_ids: list[UUID], user_id: UUID
    ) -> tuple[list[UUID], list[str]]:
        """Resolve owned attachments to base64 data URLs for a vision call.

        Returns (owned_ids, data_urls). Silently skips unreadable attachments
        so a single bad file never breaks the chat request.
        """
        owned = await self._attachments.list_by_ids(attachment_ids, user_id)
        owned_by_id = {a.id: a for a in owned}
        # Preserve caller-supplied ordering.
        ordered = [owned_by_id[a] for a in attachment_ids if a in owned_by_id]

        ids: list[UUID] = []
        urls: list[str] = []
        for attachment in ordered:
            if not attachment.is_image:
                continue
            try:
                urls.append(await self.to_data_url(attachment))
                ids.append(attachment.id)
            except Exception as exc:
                logger.warning(
                    "attachment_read_failed",
                    attachment_id=str(attachment.id),
                    error=str(exc),
                )
        return ids, urls
