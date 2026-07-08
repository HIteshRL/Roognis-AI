"""Unit tests for v0.71 generative media — image + video services (no GPU/network)."""
from uuid import uuid4

import pytest

from src.application.services.attachment_service import AttachmentService
from src.application.services.response_image_service import ResponseImageService
from src.application.services.video_generation_service import VideoGenerationService
from src.domain.entities.attachment import MessageAttachment
from src.domain.exceptions import AuthorizationError, EntityNotFound
from src.infrastructure.imagegen.base import AbstractImageGenerator, ImageResult
from src.infrastructure.imagegen.stub_provider import StubImageGenerator
from src.infrastructure.videogen.stub_provider import StubVideoGenerator

# ── Fakes ────────────────────────────────────────────────────────────────────


class _FakeStorage:
    def __init__(self):
        self.saved: dict[str, bytes] = {}

    async def save(self, file_bytes: bytes, destination: str) -> str:
        self.saved[destination] = file_bytes
        return destination

    async def read(self, storage_path: str) -> bytes:
        return self.saved[storage_path]

    async def delete(self, storage_path: str) -> None:
        self.saved.pop(storage_path, None)

    async def exists(self, storage_path: str) -> bool:
        return storage_path in self.saved


class _FakeAttachmentRepo:
    def __init__(self):
        self.rows: dict[str, MessageAttachment] = {}

    async def create(self, attachment):
        self.rows[str(attachment.id)] = attachment
        return attachment

    async def get_by_id(self, attachment_id):
        return self.rows.get(str(attachment_id))

    async def list_by_ids(self, ids, user_id):
        return [a for a in self.rows.values() if a.id in ids and a.user_id == user_id]

    async def list_by_message(self, message_id):
        return [a for a in self.rows.values() if a.message_id == message_id]

    async def list_by_messages(self, message_ids):
        return [a for a in self.rows.values() if a.message_id in message_ids]

    async def link_to_message(self, ids, message_id):
        for aid in ids:
            row = self.rows.get(str(aid))
            if row:
                row.message_id = message_id


class _ExplodingImageGenerator(AbstractImageGenerator):
    @property
    def provider_name(self):
        return "boom"

    async def generate(self, prompt, size="1024x1024"):
        raise RuntimeError("provider down")


class _FakeMessageRepo:
    def __init__(self, message=None):
        self._message = message

    async def get_by_id(self, message_id):
        return self._message


class _FakeConversationRepo:
    def __init__(self, conversation=None):
        self._conversation = conversation

    async def get_by_id(self, conversation_id):
        return self._conversation


class _FakeJobRepo:
    def __init__(self):
        self.created = []

    async def create(self, job):
        self.created.append(job)
        return job

    async def get_by_id(self, job_id):
        for j in self.created:
            if j.id == job_id:
                return j
        return None

    async def update(self, job):
        return job

    async def list_by_message(self, message_id):
        return [j for j in self.created if j.message_id == message_id]


# ── Stub providers ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_stub_image_generator_returns_png():
    result = await StubImageGenerator().generate("a cell diagram")
    assert isinstance(result, ImageResult)
    assert result.content_type == "image/png"
    assert result.data.startswith(b"\x89PNG")


def test_stub_video_generator_returns_mp4():
    result = StubVideoGenerator().generate("photosynthesis explainer", num_frames=8, fps=8)
    assert result.content_type == "video/mp4"
    assert len(result.data) > 0


# ── ResponseImageService ─────────────────────────────────────────────────────


def _image_service(gen):
    repo = _FakeAttachmentRepo()
    att_svc = AttachmentService(
        attachment_repo=repo,
        storage=_FakeStorage(),
        allowed_image_types=["image/png", "image/jpeg"],
        max_image_size_bytes=8 * 1024 * 1024,
    )
    return ResponseImageService(gen, att_svc, repo), repo


def test_build_prompt_includes_concept_and_subject():
    svc, _ = _image_service(StubImageGenerator())
    prompt = svc.build_prompt(
        question="why is the sky blue?",
        primary_concept="Rayleigh scattering",
        subject="Physics",
        chapter="Light",
    )
    assert "Rayleigh scattering" in prompt
    assert "Physics" in prompt and "Light" in prompt


@pytest.mark.asyncio
async def test_generate_is_fail_open():
    svc, _ = _image_service(_ExplodingImageGenerator())
    assert await svc.generate("anything") is None


@pytest.mark.asyncio
async def test_persist_creates_and_links_attachment(user_id):
    svc, repo = _image_service(StubImageGenerator())
    result = await svc.generate("a diagram")
    message_id = uuid4()
    attachment = await svc.persist(user_id, message_id, result)
    assert attachment is not None
    assert attachment.kind == "image"
    assert repo.rows[str(attachment.id)].message_id == message_id


# ── VideoGenerationService (request / get_job / prompt) ───────────────────────


def _video_service(message=None, conversation=None, job_repo=None):
    return VideoGenerationService(
        video_generator=StubVideoGenerator(),
        job_repo=job_repo or _FakeJobRepo(),
        message_repo=_FakeMessageRepo(message),
        conversation_repo=_FakeConversationRepo(conversation),
        storage_path="./_test_uploads",
        num_frames=8,
        fps=8,
        max_concurrent=1,
    )


@pytest.mark.asyncio
async def test_request_creates_queued_job(user_id, sample_conversation, sample_message):
    job_repo = _FakeJobRepo()
    svc = _video_service(sample_message, sample_conversation, job_repo)
    job = await svc.request(user_id, sample_message.id)
    assert job.status == "queued"
    assert job.message_id == sample_message.id
    assert job.prompt  # non-empty
    assert job_repo.created == [job]


@pytest.mark.asyncio
async def test_request_missing_message_raises(user_id):
    svc = _video_service(message=None)
    with pytest.raises(EntityNotFound):
        await svc.request(user_id, uuid4())


@pytest.mark.asyncio
async def test_request_wrong_owner_raises(sample_conversation, sample_message):
    svc = _video_service(sample_message, sample_conversation)
    with pytest.raises(AuthorizationError):
        await svc.request(uuid4(), sample_message.id)


@pytest.mark.asyncio
async def test_get_job_ownership(user_id, sample_conversation, sample_message):
    job_repo = _FakeJobRepo()
    svc = _video_service(sample_message, sample_conversation, job_repo)
    job = await svc.request(user_id, sample_message.id)

    fetched = await svc.get_job(job.id, user_id)
    assert fetched.id == job.id
    with pytest.raises(AuthorizationError):
        await svc.get_job(job.id, uuid4())
