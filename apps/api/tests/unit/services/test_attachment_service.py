"""Unit tests for Phase 0.7 AttachmentService — validation, storage, data URLs."""
import base64
from uuid import uuid4

import pytest

from src.application.services.attachment_service import AttachmentService
from src.domain.entities.attachment import MessageAttachment
from src.domain.exceptions import AuthorizationError, EntityNotFound, ValidationError


class _FakeStorage:
    """In-memory stand-in for AbstractFileStorage."""

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


class _FakeRepo:
    """In-memory stand-in for AbstractMessageAttachmentRepository."""

    def __init__(self):
        self.rows: dict[str, MessageAttachment] = {}

    async def create(self, attachment: MessageAttachment) -> MessageAttachment:
        self.rows[str(attachment.id)] = attachment
        return attachment

    async def get_by_id(self, attachment_id):
        return self.rows.get(str(attachment_id))

    async def list_by_ids(self, attachment_ids, user_id):
        return [
            a
            for a in self.rows.values()
            if a.id in attachment_ids and a.user_id == user_id
        ]

    async def list_by_message(self, message_id):
        return [a for a in self.rows.values() if a.message_id == message_id]

    async def list_by_messages(self, message_ids):
        return [a for a in self.rows.values() if a.message_id in message_ids]

    async def link_to_message(self, attachment_ids, message_id):
        for aid in attachment_ids:
            row = self.rows.get(str(aid))
            if row:
                row.message_id = message_id


_ALLOWED = ["image/jpeg", "image/png", "image/webp", "image/gif"]
_MAX = 4 * 1024 * 1024


@pytest.fixture
def storage():
    return _FakeStorage()


@pytest.fixture
def repo():
    return _FakeRepo()


@pytest.fixture
def service(repo, storage):
    return AttachmentService(
        attachment_repo=repo,
        storage=storage,
        allowed_image_types=_ALLOWED,
        max_image_size_bytes=_MAX,
    )


@pytest.mark.asyncio
async def test_upload_stores_and_persists(service, storage, repo, user_id):
    attachment = await service.upload_image(
        user_id=user_id,
        filename="pic.png",
        file_bytes=b"\x89PNG data",
        content_type="image/png",
    )
    assert attachment.user_id == user_id
    assert attachment.content_type == "image/png"
    assert attachment.file_size == len(b"\x89PNG data")
    assert str(attachment.id) in repo.rows
    assert attachment.storage_path in storage.saved


@pytest.mark.asyncio
async def test_upload_rejects_unsupported_type(service, user_id):
    with pytest.raises(ValidationError):
        await service.upload_image(
            user_id=user_id,
            filename="doc.pdf",
            file_bytes=b"%PDF",
            content_type="application/pdf",
        )


@pytest.mark.asyncio
async def test_upload_rejects_oversized_image(service, user_id):
    with pytest.raises(ValidationError):
        await service.upload_image(
            user_id=user_id,
            filename="big.png",
            file_bytes=b"x" * (_MAX + 1),
            content_type="image/png",
        )


@pytest.mark.asyncio
async def test_upload_rejects_empty_file(service, user_id):
    with pytest.raises(ValidationError):
        await service.upload_image(
            user_id=user_id,
            filename="empty.png",
            file_bytes=b"",
            content_type="image/png",
        )


@pytest.mark.asyncio
async def test_content_type_with_charset_suffix_is_normalised(service, user_id):
    attachment = await service.upload_image(
        user_id=user_id,
        filename="pic.jpg",
        file_bytes=b"jpegdata",
        content_type="image/jpeg; charset=binary",
    )
    assert attachment.content_type == "image/jpeg"


@pytest.mark.asyncio
async def test_get_owned_rejects_other_user(service, user_id):
    attachment = await service.upload_image(
        user_id=user_id,
        filename="pic.png",
        file_bytes=b"data",
        content_type="image/png",
    )
    with pytest.raises(AuthorizationError):
        await service.get_owned(attachment.id, uuid4())


@pytest.mark.asyncio
async def test_get_owned_missing_raises(service, user_id):
    with pytest.raises(EntityNotFound):
        await service.get_owned(uuid4(), user_id)


@pytest.mark.asyncio
async def test_to_data_url_round_trips_bytes(service, user_id):
    raw = b"\x89PNG binary bytes"
    attachment = await service.upload_image(
        user_id=user_id,
        filename="pic.png",
        file_bytes=raw,
        content_type="image/png",
    )
    data_url = await service.to_data_url(attachment)
    assert data_url.startswith("data:image/png;base64,")
    encoded = data_url.split(",", 1)[1]
    assert base64.b64decode(encoded) == raw


@pytest.mark.asyncio
async def test_data_urls_for_preserves_order_and_ownership(service, user_id):
    first = await service.upload_image(user_id, "a.png", b"aaa", "image/png")
    second = await service.upload_image(user_id, "b.png", b"bbb", "image/png")

    ids, urls = await service.data_urls_for([second.id, first.id], user_id)
    assert ids == [second.id, first.id]
    assert len(urls) == 2


@pytest.mark.asyncio
async def test_data_urls_for_skips_unowned(service, user_id):
    mine = await service.upload_image(user_id, "a.png", b"aaa", "image/png")
    theirs = await service.upload_image(uuid4(), "b.png", b"bbb", "image/png")

    ids, urls = await service.data_urls_for([mine.id, theirs.id], user_id)
    assert ids == [mine.id]
    assert len(urls) == 1
