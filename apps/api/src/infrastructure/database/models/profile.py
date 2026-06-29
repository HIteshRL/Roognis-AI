from sqlalchemy import Boolean, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.database.base import Base, TimestampMixin, UUIDMixin


class ProfileModel(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "profiles"

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    full_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    timezone: Mapped[str] = mapped_column(String(100), default="UTC", nullable=False)
    language: Mapped[str] = mapped_column(String(10), default="en", nullable=False)

    user: Mapped["UserModel"] = relationship(back_populates="profile")  # type: ignore[name-defined]  # noqa: F821


class SettingsModel(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "settings"

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    theme: Mapped[str] = mapped_column(String(20), default="dark", nullable=False)
    notifications_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    llm_model: Mapped[str] = mapped_column(
        String(100), default="llama-3.3-70b-versatile", nullable=False
    )
    temperature: Mapped[float] = mapped_column(Float, default=0.7, nullable=False)

    user: Mapped["UserModel"] = relationship(back_populates="settings")  # type: ignore[name-defined]  # noqa: F821
