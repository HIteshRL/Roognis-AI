from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4


@dataclass
class Profile:
    user_id: UUID
    id: UUID = field(default_factory=uuid4)
    full_name: str | None = None
    avatar_url: str | None = None
    bio: str | None = None
    timezone: str = "UTC"
    language: str = "en"
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def update(
        self,
        full_name: str | None = None,
        bio: str | None = None,
        timezone: str | None = None,
        language: str | None = None,
    ) -> None:
        if full_name is not None:
            self.full_name = full_name
        if bio is not None:
            self.bio = bio
        if timezone is not None:
            self.timezone = timezone
        if language is not None:
            self.language = language
        self.updated_at = datetime.now(UTC)


@dataclass
class Settings:
    user_id: UUID
    id: UUID = field(default_factory=uuid4)
    theme: str = "dark"
    notifications_enabled: bool = True
    llm_model: str = "llama-3.3-70b-versatile"
    temperature: float = 0.7
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


