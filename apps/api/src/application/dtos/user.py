from typing import Literal

from pydantic import BaseModel, Field


class UpdateProfileRequest(BaseModel):
    full_name: str | None = Field(default=None, max_length=200)
    bio: str | None = Field(default=None, max_length=1000)
    timezone: str | None = None
    language: str | None = None


class ProfileResponse(BaseModel):
    id: str
    user_id: str
    full_name: str | None
    avatar_url: str | None
    bio: str | None
    timezone: str
    language: str
    created_at: str
    updated_at: str


class UpdateSettingsRequest(BaseModel):
    theme: Literal["light", "dark", "system"] | None = None
    notifications_enabled: bool | None = None
    llm_model: str | None = None
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)


class SettingsResponse(BaseModel):
    id: str
    user_id: str
    theme: str
    notifications_enabled: bool
    llm_model: str
    temperature: float
    created_at: str
    updated_at: str


class UserResponse(BaseModel):
    id: str
    email: str
    username: str
    is_active: bool
    is_verified: bool
    created_at: str
    updated_at: str
