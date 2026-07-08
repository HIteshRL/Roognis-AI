from pydantic import UUID4, BaseModel, Field


class SendMessageRequest(BaseModel):
    message: str = Field(min_length=1, max_length=32000)
    conversation_id: UUID4 | None = None
    subject: str | None = None
    chapter: str | None = None
    attachment_ids: list[UUID4] | None = None


class AttachmentResponse(BaseModel):
    id: str
    kind: str
    content_type: str
    file_size: int
    url: str
    created_at: str


class ConversationResponse(BaseModel):
    id: str
    user_id: str
    title: str | None
    subject: str | None = None
    chapter: str | None = None
    is_archived: bool
    created_at: str
    updated_at: str
    message_count: int = 0


class SubjectCountResponse(BaseModel):
    subject: str
    count: int


class MessageResponse(BaseModel):
    id: str
    conversation_id: str
    role: str
    content: str
    token_count: int | None
    created_at: str
    attachments: list[AttachmentResponse] = []


class ConversationWithMessagesResponse(BaseModel):
    conversation: ConversationResponse
    messages: list[MessageResponse]
