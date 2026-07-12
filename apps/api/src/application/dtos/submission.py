from pydantic import BaseModel, Field


class SubmitRequest(BaseModel):
    text_answer: str | None = Field(default=None, max_length=100000)


class GradeRequest(BaseModel):
    score: float = Field(ge=0)
    rubric_scores: list[dict] | None = None  # [{criterion, points}]
    comment: str | None = Field(default=None, max_length=5000)
    private_feedback: str | None = Field(default=None, max_length=5000)
    return_to_student: bool = True


class SubmissionAttachmentResponse(BaseModel):
    id: str
    filename: str
    file_type: str | None
    file_size: int
    created_at: str


class GradeResponse(BaseModel):
    id: str
    grader_id: str | None
    score: float
    max_marks: float | None
    rubric_scores: list | None
    comment: str | None
    private_feedback: str | None = None  # omitted in teacher-to-peer contexts, kept for student
    is_returned: bool
    is_regrade: bool
    created_at: str


class SubmissionResponse(BaseModel):
    id: str
    coursework_id: str
    student_id: str
    student_name: str | None = None
    status: str
    text_answer: str | None
    attempt: int
    is_late: bool
    submitted_at: str | None
    attachments: list[SubmissionAttachmentResponse] = []
    grade: GradeResponse | None = None
    grade_history: list[GradeResponse] = []
    created_at: str
    updated_at: str


class SubmissionListResponse(BaseModel):
    items: list[SubmissionResponse]
    total: int
    page: int
    limit: int
