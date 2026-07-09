from uuid import UUID

import structlog

from src.application.services.attachment_service import AttachmentService
from src.domain.entities.attachment import MessageAttachment
from src.domain.repositories.attachment_repository import (
    AbstractMessageAttachmentRepository,
)
from src.infrastructure.imagegen.base import AbstractImageGenerator, ImageResult

logger = structlog.get_logger(__name__)

_MAX_PROMPT_CHARS = 500


class ResponseImageService:
    """Generates the default illustrative image that accompanies each answer.

    Generation (network/GPU) is separated from persistence so the caller can
    overlap generation with text streaming, then persist + link once the
    assistant message exists. Fail-open throughout — a failure returns None and
    the text answer is unaffected.
    """

    def __init__(
        self,
        image_generator: AbstractImageGenerator,
        attachment_svc: AttachmentService,
        attachment_repo: AbstractMessageAttachmentRepository,
        image_size: str = "1024x1024",
    ) -> None:
        self._generator = image_generator
        self._attachments = attachment_svc
        self._attachment_repo = attachment_repo
        self._size = image_size

    def build_prompt(
        self,
        question: str,
        primary_concept: str | None,
        subject: str | None,
        chapter: str | None,
    ) -> str:
        focus = primary_concept or question
        parts = [
            f"Clear, educational illustration explaining: {focus}.",
        ]
        if subject:
            scope = subject
            if chapter:
                scope += f" — {chapter}"
            parts.append(f"Subject context: {scope}.")
        parts.append(
            "Simple, labelled, classroom-friendly diagram style. "
            "No text-heavy content, age-appropriate, no watermarks."
        )
        return " ".join(parts)[:_MAX_PROMPT_CHARS]

    async def generate(self, prompt: str) -> ImageResult | None:
        try:
            return await self._generator.generate(prompt, size=self._size)
        except Exception as exc:
            logger.warning("response_image_generate_failed", error=str(exc))
            return None

    async def persist(
        self, user_id: UUID, message_id: UUID, result: ImageResult
    ) -> MessageAttachment | None:
        try:
            ext = "png" if "png" in result.content_type else "jpg"
            attachment = await self._attachments.upload_image(
                user_id=user_id,
                filename=f"generated.{ext}",
                file_bytes=result.data,
                content_type=result.content_type,
            )
            await self._attachment_repo.link_to_message([attachment.id], message_id)
            return attachment
        except Exception as exc:
            logger.warning("response_image_persist_failed", error=str(exc))
            return None
