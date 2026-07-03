import asyncio
from uuid import UUID, uuid4

import structlog

from src.domain.entities.attachment import MessageAttachment
from src.domain.entities.media_job import MediaJob
from src.domain.exceptions import AuthorizationError, EntityNotFound
from src.domain.repositories.conversation_repository import (
    AbstractConversationRepository,
    AbstractMessageRepository,
)
from src.domain.repositories.media_job_repository import AbstractMediaJobRepository
from src.infrastructure.database.repositories.attachment_repository import (
    MessageAttachmentRepository,
)
from src.infrastructure.database.repositories.media_job_repository import (
    MediaJobRepository,
)
from src.infrastructure.database.session import AsyncSessionLocal
from src.infrastructure.storage.local_storage import LocalFileStorage
from src.infrastructure.videogen.base import AbstractVideoGenerator

logger = structlog.get_logger(__name__)

_MAX_PROMPT_CHARS = 400

# Process-wide GPU guard so concurrent requests don't OOM the card. Created
# lazily on first use so it binds to the running event loop.
_video_semaphore: asyncio.Semaphore | None = None


def _get_semaphore(limit: int) -> asyncio.Semaphore:
    global _video_semaphore
    if _video_semaphore is None:
        _video_semaphore = asyncio.Semaphore(max(1, limit))
    return _video_semaphore


class VideoGenerationService:
    """On-demand video generation as an async job.

    `request` runs in the request path (request-scoped repos). `run` runs in a
    BackgroundTask after the response — it opens its own DB session (mirroring
    IngestionPipeline.run) because the request session is already closed.
    Fail-open: `run` never raises; failures land on the job as status=failed.
    """

    def __init__(
        self,
        video_generator: AbstractVideoGenerator,
        job_repo: AbstractMediaJobRepository,
        message_repo: AbstractMessageRepository,
        conversation_repo: AbstractConversationRepository,
        storage_path: str,
        num_frames: int = 97,
        fps: int = 24,
        max_concurrent: int = 1,
    ) -> None:
        self._generator = video_generator
        self._jobs = job_repo
        self._messages = message_repo
        self._conversations = conversation_repo
        self._storage_path = storage_path
        self._num_frames = num_frames
        self._fps = fps
        self._max_concurrent = max_concurrent

    def _build_prompt(self, answer_text: str) -> str:
        cleaned = " ".join(answer_text.split())
        base = (
            "Short educational explainer animation illustrating this lesson: "
            f"{cleaned}. Clear, simple, classroom-friendly visuals."
        )
        return base[:_MAX_PROMPT_CHARS]

    async def request(self, user_id: UUID, message_id: UUID) -> MediaJob:
        message = await self._messages.get_by_id(message_id)
        if not message:
            raise EntityNotFound("Message not found")

        conversation = await self._conversations.get_by_id(message.conversation_id)
        if not conversation:
            raise EntityNotFound("Conversation not found")
        if conversation.user_id != user_id:
            raise AuthorizationError("Access denied")

        prompt = self._build_prompt(message.content)
        job = MediaJob(
            user_id=user_id,
            message_id=message_id,
            conversation_id=conversation.id,
            kind="video",
            status="queued",
            prompt=prompt,
        )
        return await self._jobs.create(job)

    async def get_job(self, job_id: UUID, user_id: UUID) -> MediaJob:
        job = await self._jobs.get_by_id(job_id)
        if not job:
            raise EntityNotFound("Job not found")
        if job.user_id != user_id:
            raise AuthorizationError("Access denied")
        return job

    async def run(self, job_id: UUID) -> None:
        # 1. Mark running (own session).
        async with AsyncSessionLocal() as db:
            job_repo = MediaJobRepository(db)
            job = await job_repo.get_by_id(job_id)
            if job is None or job.is_terminal:
                return
            job.status = "running"
            job.progress = 10
            await job_repo.update(job)
            await db.commit()

        # 2. Generate (blocking torch) off the event loop, under the GPU guard.
        try:
            async with _get_semaphore(self._max_concurrent):
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None, self._generator.generate, job.prompt, self._num_frames, self._fps
                )
        except Exception as exc:
            logger.warning("video_job_failed", job_id=str(job_id), error=str(exc))
            await self._fail(job_id, str(exc))
            return

        # 3. Persist the mp4 + attachment, mark completed (own session).
        try:
            async with AsyncSessionLocal() as db:
                storage = LocalFileStorage(self._storage_path)
                attachment_repo = MessageAttachmentRepository(db)
                job_repo = MediaJobRepository(db)

                attachment_id = uuid4()
                destination = f"chat/{job.user_id}/{attachment_id}.mp4"
                storage_path = await storage.save(result.data, destination)

                attachment = MessageAttachment(
                    id=attachment_id,
                    user_id=job.user_id,
                    message_id=job.message_id,
                    storage_path=storage_path,
                    content_type=result.content_type,
                    file_size=len(result.data),
                    kind="video",
                )
                await attachment_repo.create(attachment)

                fresh = await job_repo.get_by_id(job_id)
                if fresh is not None:
                    fresh.status = "completed"
                    fresh.progress = 100
                    fresh.attachment_id = attachment.id
                    await job_repo.update(fresh)
                await db.commit()
            logger.info("video_job_completed", job_id=str(job_id))
        except Exception as exc:
            logger.warning("video_job_persist_failed", job_id=str(job_id), error=str(exc))
            await self._fail(job_id, str(exc))

    async def _fail(self, job_id: UUID, error: str) -> None:
        try:
            async with AsyncSessionLocal() as db:
                job_repo = MediaJobRepository(db)
                job = await job_repo.get_by_id(job_id)
                if job is not None:
                    job.status = "failed"
                    job.error_message = error[:2000]
                    await job_repo.update(job)
                await db.commit()
        except Exception as exc:
            logger.error("video_job_fail_update_error", job_id=str(job_id), error=str(exc))
