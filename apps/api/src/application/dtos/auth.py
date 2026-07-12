from typing import Literal

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=30, pattern=r"^[a-zA-Z0-9_-]+$")
    password: str = Field(min_length=8, max_length=128)
    role: Literal["student", "teacher"] = "student"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class ClerkSyncRequest(BaseModel):
    clerk_id: str
    email: EmailStr
    username: str | None = None


class TokenPayload(BaseModel):
    sub: str  # user_id
    email: str
    exp: int


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=16)


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str = Field(min_length=16)
    new_password: str = Field(min_length=8, max_length=128)


class EmailVerifyConfirm(BaseModel):
    token: str = Field(min_length=16)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=8, max_length=128)
