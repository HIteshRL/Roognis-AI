from pydantic import UUID4, BaseModel, Field


class SendMessageRequest(BaseModel):
    message: str = Field(min_length=1, max_length=32000)
    conversation_id: UUID4 | None = None
    chapter_id: UUID4 | None = None  # scope inference to a classroom chapter's content


class ConversationResponse(BaseModel):
    id: str
    user_id: str
    title: str | None
    is_archived: bool
    created_at: str
    updated_at: str
    message_count: int = 0


class MessageResponse(BaseModel):
    id: str
    conversation_id: str
    role: str
    content: str
    token_count: int | None
    created_at: str


class ConversationWithMessagesResponse(BaseModel):
    conversation: ConversationResponse
    messages: list[MessageResponse]
