from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base, UUIDMixin


class PsychometricResponseModel(Base, UUIDMixin):
    __tablename__ = "psychometric_responses"
    __table_args__ = (UniqueConstraint("user_id", "question_key"),)

    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    question_key: Mapped[str] = mapped_column(String(60), nullable=False)
    question_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    dimension: Mapped[str] = mapped_column(String(30), nullable=False)
    response_value: Mapped[str] = mapped_column(String(60), nullable=False)
    response_raw: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
