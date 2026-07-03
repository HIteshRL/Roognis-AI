from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4


@dataclass
class MessageAttachment:
    user_id: UUID
    storage_path: str
    content_type: str
    file_size: int
    id: UUID = field(default_factory=uuid4)
    message_id: UUID | None = None
    kind: str = "image"
    width: int | None = None
    height: int | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def is_image(self) -> bool:
        return self.kind == "image" and self.content_type.startswith("image/")
