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
