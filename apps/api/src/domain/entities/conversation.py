from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4


@dataclass
class Conversation:
    user_id: UUID
    id: UUID = field(default_factory=uuid4)
    title: str | None = None
    is_archived: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def set_title(self, title: str) -> None:
        self.title = title
        self.updated_at = datetime.utcnow()

    def archive(self) -> None:
        self.is_archived = True
        self.updated_at = datetime.utcnow()


@dataclass
class Message:
    conversation_id: UUID
    role: str  # 'user' | 'assistant' | 'system'
    content: str
    id: UUID = field(default_factory=uuid4)
    token_count: int | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
