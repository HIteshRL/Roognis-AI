from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base, TimestampMixin, UUIDMixin


class FaqEntryModel(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "faq_entries"

    cache_key: Mapped[str] = mapped_column(String(80), unique=True, nullable=False, index=True)
    normalized_query: Mapped[str] = mapped_column(Text, nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    subject: Mapped[str | None] = mapped_column(String(200), nullable=True, index=True)
    grade: Mapped[str | None] = mapped_column(String(100), nullable=True)
    hit_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1, index=True)
    source: Mapped[str] = mapped_column(String(30), nullable=False, default="hot_query")
    last_hit_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
