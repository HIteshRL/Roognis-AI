from typing import Literal

from pydantic import BaseModel, Field

MaterialCategory = Literal[
    "note", "assignment", "reference", "question_paper", "solution", "other"
]


# ── Folders ──────────────────────────────────────────────────────────────────

class CreateFolderRequest(BaseModel):
    name: str = Field(min_length=1, max_length=300)
    parent_id: str | None = None


class UpdateFolderRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=300)
    parent_id: str | None = None  # move under a new parent ("" clears to root)


class FolderResponse(BaseModel):
    id: str
    classroom_id: str
    parent_id: str | None
    name: str
    is_deleted: bool
    created_at: str
    updated_at: str


# ── Materials ────────────────────────────────────────────────────────────────

class CreateLinkMaterialRequest(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    link_url: str = Field(min_length=1, max_length=2000)
    description: str | None = Field(default=None, max_length=2000)
    category: MaterialCategory = "reference"
    folder_id: str | None = None


class UpdateMaterialRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=500)
    description: str | None = Field(default=None, max_length=2000)
    category: MaterialCategory | None = None


class MoveMaterialRequest(BaseModel):
    folder_id: str | None = None  # None moves to classroom root


class MaterialResponse(BaseModel):
    id: str
    classroom_id: str
    folder_id: str | None
    uploaded_by: str
    title: str
    description: str | None
    category: str
    filename: str | None
    file_type: str | None
    file_size: int
    link_url: str | None
    version: int
    download_count: int
    is_deleted: bool
    is_bookmarked: bool = False
    progress: float | None = None
    created_at: str
    updated_at: str


class MaterialListResponse(BaseModel):
    items: list[MaterialResponse]
    total: int
    page: int
    limit: int


class MaterialVersionResponse(BaseModel):
    id: str
    version: int
    filename: str | None
    file_size: int
    uploaded_by: str | None
    created_at: str


class RecordViewRequest(BaseModel):
    progress: float | None = Field(default=None, ge=0.0, le=1.0)
