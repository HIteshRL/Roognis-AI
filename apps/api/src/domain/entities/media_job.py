from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4


@dataclass
class MediaJob:
    user_id: UUID
    message_id: UUID
    prompt: str
    id: UUID = field(default_factory=uuid4)
    conversation_id: UUID | None = None
    kind: str = "video"
    status: str = "queued"  # queued | running | completed | failed
    attachment_id: UUID | None = None
    progress: int = 0
    error_message: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def is_terminal(self) -> bool:
        return self.status in ("completed", "failed")

    @property
    def is_done(self) -> bool:
        return self.status == "completed"
