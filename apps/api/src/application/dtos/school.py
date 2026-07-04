from pydantic import BaseModel, Field

# ── School ───────────────────────────────────────────────────────────────────


class CreateSchoolRequest(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    address: str | None = Field(default=None, max_length=2000)


class SchoolResponse(BaseModel):
    id: str
    name: str
    slug: str
    address: str | None
    is_active: bool
    my_role: str
    created_at: str
    updated_at: str


class AddTeacherRequest(BaseModel):
    email: str = Field(max_length=255)
    role: str = Field(default="teacher")


class SchoolMemberResponse(BaseModel):
    id: str
    user_id: str
    email: str
    username: str
    role: str
    status: str


# ── Classroom ────────────────────────────────────────────────────────────────


class CreateClassroomRequest(BaseModel):
    school_id: str
    name: str = Field(min_length=1, max_length=200)
    subject: str | None = Field(default=None, max_length=200)
    grade: str | None = Field(default=None, max_length=100)
    description: str | None = Field(default=None, max_length=2000)


class UpdateClassroomRequest(BaseModel):
    name: str | None = Field(default=None, max_length=200)
    subject: str | None = Field(default=None, max_length=200)
    grade: str | None = Field(default=None, max_length=100)
    description: str | None = Field(default=None, max_length=2000)
    is_active: bool | None = None


class ClassroomResponse(BaseModel):
    id: str
    school_id: str
    name: str
    subject: str | None
    grade: str | None
    teacher_id: str | None
    join_code: str
    description: str | None
    is_active: bool
    student_count: int = 0
    syllabus_count: int = 0
    created_at: str
    updated_at: str


class JoinClassroomRequest(BaseModel):
    join_code: str = Field(min_length=4, max_length=16)


class RosterEntryResponse(BaseModel):
    enrollment_id: str
    student_id: str
    username: str
    email: str
    status: str
    enrolled_at: str


# ── Syllabus ─────────────────────────────────────────────────────────────────


class CreateSyllabusItemRequest(BaseModel):
    subject: str = Field(min_length=1, max_length=200)
    chapter: str = Field(min_length=1, max_length=200)
    topic: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=4000)
    order_index: int = 0
    knowledge_base_id: str | None = None
    is_published: bool = False


class UpdateSyllabusItemRequest(BaseModel):
    subject: str | None = Field(default=None, max_length=200)
    chapter: str | None = Field(default=None, max_length=200)
    topic: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=4000)
    order_index: int | None = None
    knowledge_base_id: str | None = None
    is_published: bool | None = None


class SyllabusItemResponse(BaseModel):
    id: str
    classroom_id: str
    subject: str
    chapter: str
    topic: str | None
    description: str | None
    order_index: int
    knowledge_base_id: str | None
    is_published: bool
    created_at: str
    updated_at: str
