from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

CourseworkType = Literal[
    "announcement", "assignment", "homework", "quiz", "exam",
    "practice_set", "discussion", "poll",
]


class RubricCriterion(BaseModel):
    criterion: str = Field(min_length=1, max_length=300)
    description: str | None = Field(default=None, max_length=1000)
    max_points: float = Field(gt=0)


class CreateCourseworkRequest(BaseModel):
    type: CourseworkType
    title: str = Field(min_length=1, max_length=300)
    body: str | None = Field(default=None, max_length=50000)
    due_at: datetime | None = None
    allow_late: bool = True
    max_marks: float | None = Field(default=None, ge=0)
    rubric: list[RubricCriterion] | None = None
    questions: list[dict] | None = None  # quiz/exam/practice_set payloads
    poll_options: list[str] | None = None
    settings: dict | None = None
    publish: bool = False  # publish immediately instead of saving a draft
    scheduled_at: datetime | None = None  # schedule future publishing


class UpdateCourseworkRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    body: str | None = Field(default=None, max_length=50000)
    due_at: datetime | None = None
    allow_late: bool | None = None
    max_marks: float | None = Field(default=None, ge=0)
    rubric: list[RubricCriterion] | None = None
    questions: list[dict] | None = None
    poll_options: list[str] | None = None
    settings: dict | None = None
    expected_version: int | None = Field(
        default=None, ge=1,
        description="Optimistic-locking token; 409 if the record changed since it was read",
    )


class ScheduleRequest(BaseModel):
    scheduled_at: datetime


class AddAttachmentRequest(BaseModel):
    material_id: str | None = None
    link_url: str | None = Field(default=None, max_length=2000)
    title: str | None = Field(default=None, max_length=500)


class PollVoteRequest(BaseModel):
    option_index: int = Field(ge=0)


class CourseworkAttachmentResponse(BaseModel):
    id: str
    material_id: str | None
    link_url: str | None
    title: str | None


class CourseworkResponse(BaseModel):
    id: str
    classroom_id: str
    author_id: str
    type: str
    title: str
    body: str | None
    status: str
    scheduled_at: str | None
    published_at: str | None
    due_at: str | None
    allow_late: bool
    max_marks: float | None
    rubric: list | None
    questions: list | None
    poll_options: list | None
    settings: dict
    version: int
    attachments: list[CourseworkAttachmentResponse] = []
    submission_count: int | None = None
    graded_count: int | None = None
    my_submission_status: str | None = None
    poll_results: dict[int, int] | None = None
    my_poll_vote: int | None = None
    created_at: str
    updated_at: str


class CourseworkListResponse(BaseModel):
    items: list[CourseworkResponse]
    total: int
    page: int
    limit: int
