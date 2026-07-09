from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4


@dataclass
class FaqEntry:
    cache_key: str
    question: str
    answer: str
    id: UUID = field(default_factory=uuid4)
    normalized_query: str = ""
    subject: str | None = None
    grade: str | None = None
    hit_count: int = 1
    source: str = "hot_query"
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    last_hit_at: datetime = field(default_factory=lambda: datetime.now(UTC))
