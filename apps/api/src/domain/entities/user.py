from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4


@dataclass
class User:
    email: str
    username: str
    password_hash: str
    id: UUID = field(default_factory=uuid4)
    is_active: bool = True
    is_verified: bool = False
    is_admin: bool = False
    role: str = "student"
    clerk_id: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def deactivate(self) -> None:
        self.is_active = False
        self.updated_at = datetime.now(UTC)

    def verify(self) -> None:
        self.is_verified = True
        self.updated_at = datetime.now(UTC)

    def link_clerk(self, clerk_id: str) -> None:
        self.clerk_id = clerk_id
        self.updated_at = datetime.now(UTC)


