from pydantic import BaseModel, Field


class LinkCodeResponse(BaseModel):
    code: str
    expires_in_seconds: int


class LinkRequest(BaseModel):
    code: str = Field(min_length=4, max_length=16)


class ChildSummaryResponse(BaseModel):
    link_id: str
    student_id: str
    username: str
    email: str
    grade: str | None
    linked_at: str


class GuardianSummaryResponse(BaseModel):
    link_id: str
    parent_id: str
    username: str
    email: str
    linked_at: str
