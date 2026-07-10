from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.database.base import Base, TimestampMixin, UUIDMixin


class UserModel(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    role: Mapped[str] = mapped_column(String(20), default="student", nullable=False)
    clerk_id: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True, index=True)

    profile: Mapped["ProfileModel"] = relationship(back_populates="user", uselist=False, cascade="all, delete-orphan")  # type: ignore[name-defined]  # noqa: F821
    settings: Mapped["SettingsModel"] = relationship(back_populates="user", uselist=False, cascade="all, delete-orphan")  # type: ignore[name-defined]  # noqa: F821
    conversations: Mapped[list["ConversationModel"]] = relationship(back_populates="user", cascade="all, delete-orphan")  # type: ignore[name-defined]  # noqa: F821
    sessions: Mapped[list["SessionModel"]] = relationship(back_populates="user", cascade="all, delete-orphan")  # type: ignore[name-defined]  # noqa: F821
