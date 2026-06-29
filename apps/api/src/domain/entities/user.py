from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4


@dataclass
class User:
    email: str
    username: str
    password_hash: str
    id: UUID = field(default_factory=uuid4)
    is_active: bool = True
    is_verified: bool = False
    clerk_id: str | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def deactivate(self) -> None:
        self.is_active = False
        self.updated_at = datetime.utcnow()

    def verify(self) -> None:
        self.is_verified = True
        self.updated_at = datetime.utcnow()

    def link_clerk(self, clerk_id: str) -> None:
        self.clerk_id = clerk_id
        self.updated_at = datetime.utcnow()
