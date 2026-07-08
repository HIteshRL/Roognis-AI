from pydantic import BaseModel


class MediaJobResponse(BaseModel):
    id: str
    message_id: str
    conversation_id: str | None
    kind: str
    status: str
    progress: int
    attachment_id: str | None
    url: str | None
    error_message: str | None
    created_at: str
    updated_at: str


class ChapterResponse(BaseModel):
    chapter: str
    conversation_count: int = 0
