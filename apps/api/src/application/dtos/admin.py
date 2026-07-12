from pydantic import BaseModel, EmailStr, Field


class CreateInstitutionRequest(BaseModel):
    name: str = Field(min_length=1, max_length=300)
    address: str | None = Field(default=None, max_length=2000)
    contact_email: EmailStr | None = None


class UpdateInstitutionRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=300)
    address: str | None = Field(default=None, max_length=2000)
    contact_email: EmailStr | None = None
    is_active: bool | None = None


class InstitutionResponse(BaseModel):
    id: str
    name: str
    address: str | None
    contact_email: str | None
    is_active: bool
    created_at: str


class AdminUserResponse(BaseModel):
    id: str
    email: str
    username: str
    role: str
    is_active: bool
    is_verified: bool
    is_admin: bool
    created_at: str


class AdminUserListResponse(BaseModel):
    items: list[AdminUserResponse]
    total: int
    page: int
    limit: int
