from pydantic import BaseModel, Field


class CreateCommentRequest(BaseModel):
    body: str = Field(min_length=1, max_length=10000)
    coursework_id: str | None = None  # attach to a stream item / discussion thread
    parent_id: str | None = None  # reply to another comment
    mentions: list[str] = []  # user ids


class UpdateCommentRequest(BaseModel):
    body: str = Field(min_length=1, max_length=10000)


class ReactionRequest(BaseModel):
    emoji: str = Field(min_length=1, max_length=20)


class CommentResponse(BaseModel):
    id: str
    classroom_id: str
    coursework_id: str | None
    parent_id: str | None
    author_id: str
    author_name: str | None = None
    body: str
    mentions: list
    reactions: dict[str, int] = {}
    reply_count: int = 0
    created_at: str
    updated_at: str


class CommentListResponse(BaseModel):
    items: list[CommentResponse]
    total: int
    page: int
    limit: int
