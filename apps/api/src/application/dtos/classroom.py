from pydantic import BaseModel, Field

# ── Classroom (teacher's subject) ────────────────────────────────────────────

class CreateClassroomRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    subject: str | None = Field(default=None, max_length=100)
    section: str | None = Field(default=None, max_length=100)
    room: str | None = Field(default=None, max_length=100)
    grade: str | None = Field(default=None, max_length=20)
    description: str | None = Field(default=None, max_length=2000)
    color: str | None = Field(default=None, max_length=20)


class UpdateClassroomRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    subject: str | None = Field(default=None, max_length=100)
    section: str | None = Field(default=None, max_length=100)
    room: str | None = Field(default=None, max_length=100)
    grade: str | None = Field(default=None, max_length=20)
    description: str | None = Field(default=None, max_length=2000)
    color: str | None = Field(default=None, max_length=20)


class ClassroomResponse(BaseModel):
    id: str
    teacher_id: str
    name: str
    subject: str | None
    section: str | None
    room: str | None
    grade: str | None
    description: str | None
    color: str
    join_code: str
    is_archived: bool
    student_count: int = 0
    chapter_count: int = 0
    created_at: str
    updated_at: str


# ── Chapter ──────────────────────────────────────────────────────────────────

class CreateChapterRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)


class UpdateChapterRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    is_published: bool | None = None
    order_index: int | None = Field(default=None, ge=0)


class ChapterResponse(BaseModel):
    id: str
    classroom_id: str
    knowledge_base_id: str | None
    title: str
    description: str | None
    order_index: int
    is_published: bool
    document_count: int = 0
    created_at: str
    updated_at: str


# ── Enrollment ───────────────────────────────────────────────────────────────

class JoinClassroomRequest(BaseModel):
    join_code: str = Field(min_length=4, max_length=12)


class EnrolledStudentResponse(BaseModel):
    id: str
    username: str
    email: str
    joined_at: str


class ChapterRefResponse(BaseModel):
    id: str
    title: str
    description: str | None
    order_index: int
    is_published: bool


class StudentClassroomResponse(BaseModel):
    id: str
    name: str
    subject: str | None
    section: str | None
    grade: str | None
    color: str
    teacher_name: str
    chapter_count: int = 0
    created_at: str
