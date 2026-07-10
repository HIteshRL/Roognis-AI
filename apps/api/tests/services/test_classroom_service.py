"""
Tests for the teacher persona (ClassroomService) — Google Classroom model.

Covers join-code generation, classroom/chapter creation, enrolment idempotency,
ownership enforcement, and chapter-scoped access control for student inference.
Uses lightweight in-memory repositories so no database is required.
"""
from uuid import UUID, uuid4

import pytest

from src.application.dtos.classroom import (
    CreateChapterRequest,
    CreateClassroomRequest,
    UpdateChapterRequest,
)
from src.application.services.classroom_service import ClassroomService
from src.domain.entities.classroom import (
    Classroom,
    Enrollment,
    generate_join_code,
)
from src.domain.entities.knowledge import KnowledgeBase
from src.domain.entities.user import User
from src.domain.exceptions import AuthorizationError, EntityNotFound


class _DB:
    def __init__(self):
        self.classrooms: dict[UUID, Classroom] = {}
        self.chapters: dict = {}
        self.enrollments: list[Enrollment] = []
        self.kbs: dict[UUID, KnowledgeBase] = {}
        self.users: dict[UUID, User] = {}


class FakeClassroomRepo:
    def __init__(self, db: _DB):
        self.db = db

    async def create(self, classroom):
        self.db.classrooms[classroom.id] = classroom
        return classroom

    async def get_by_id(self, classroom_id):
        return self.db.classrooms.get(classroom_id)

    async def get_by_join_code(self, join_code):
        return next((c for c in self.db.classrooms.values() if c.join_code == join_code), None)

    async def list_by_teacher(self, teacher_id, include_archived=False):
        return [
            c for c in self.db.classrooms.values()
            if c.teacher_id == teacher_id and (include_archived or not c.is_archived)
        ]

    async def update(self, classroom):
        self.db.classrooms[classroom.id] = classroom
        return classroom

    async def delete(self, classroom_id):
        self.db.classrooms.pop(classroom_id, None)

    async def count_students(self, classroom_id):
        return len([e for e in self.db.enrollments if e.classroom_id == classroom_id])

    async def count_chapters(self, classroom_id):
        return len([c for c in self.db.chapters.values() if c.classroom_id == classroom_id])


class FakeChapterRepo:
    def __init__(self, db: _DB):
        self.db = db

    async def create(self, chapter):
        self.db.chapters[chapter.id] = chapter
        return chapter

    async def get_by_id(self, chapter_id):
        return self.db.chapters.get(chapter_id)

    async def list_by_classroom(self, classroom_id):
        items = [c for c in self.db.chapters.values() if c.classroom_id == classroom_id]
        return sorted(items, key=lambda c: c.order_index)

    async def update(self, chapter):
        self.db.chapters[chapter.id] = chapter
        return chapter

    async def delete(self, chapter_id):
        self.db.chapters.pop(chapter_id, None)

    async def next_order_index(self, classroom_id):
        existing = [c for c in self.db.chapters.values() if c.classroom_id == classroom_id]
        return (max((c.order_index for c in existing), default=-1)) + 1


class FakeEnrollmentRepo:
    def __init__(self, db: _DB):
        self.db = db

    async def create(self, enrollment):
        self.db.enrollments.append(enrollment)
        return enrollment

    async def get(self, classroom_id, student_id):
        return next(
            (e for e in self.db.enrollments
             if e.classroom_id == classroom_id and e.student_id == student_id),
            None,
        )

    async def list_students(self, classroom_id):
        ids = [e.student_id for e in self.db.enrollments if e.classroom_id == classroom_id]
        return [self.db.users[i] for i in ids if i in self.db.users]

    async def list_classrooms_for_student(self, student_id):
        ids = [e.classroom_id for e in self.db.enrollments if e.student_id == student_id]
        return [self.db.classrooms[i] for i in ids if i in self.db.classrooms]

    async def is_enrolled(self, classroom_id, student_id):
        return any(
            e.classroom_id == classroom_id and e.student_id == student_id
            for e in self.db.enrollments
        )

    async def delete(self, classroom_id, student_id):
        self.db.enrollments = [
            e for e in self.db.enrollments
            if not (e.classroom_id == classroom_id and e.student_id == student_id)
        ]


class FakeKBRepo:
    def __init__(self, db: _DB):
        self.db = db

    async def create(self, kb):
        self.db.kbs[kb.id] = kb
        return kb


class FakeUserRepo:
    def __init__(self, db: _DB):
        self.db = db

    async def get_by_id(self, user_id):
        return self.db.users.get(user_id)


class FakeDocRepo:
    async def list_by_knowledge_base(self, kb_id, page, limit):
        return [], 0


@pytest.fixture
def db():
    d = _DB()
    teacher = User(email="t@x.com", username="teacher1", password_hash="", role="teacher")
    student = User(email="s@x.com", username="student1", password_hash="", role="student")
    d.users[teacher.id] = teacher
    d.users[student.id] = student
    return d


@pytest.fixture
def svc(db):
    return ClassroomService(
        classroom_repo=FakeClassroomRepo(db),
        chapter_repo=FakeChapterRepo(db),
        enrollment_repo=FakeEnrollmentRepo(db),
        kb_repo=FakeKBRepo(db),
        user_repo=FakeUserRepo(db),
        doc_repo=FakeDocRepo(),
    )


def _teacher_id(db):
    return next(u.id for u in db.users.values() if u.role == "teacher")


def _student_id(db):
    return next(u.id for u in db.users.values() if u.role == "student")


# ── Join code ─────────────────────────────────────────────────────────────────

def test_join_code_format():
    for _ in range(50):
        code = generate_join_code()
        assert len(code) == 6
        assert all(ch in "ABCDEFGHJKLMNPQRSTUVWXYZ23456789" for ch in code)
        assert "0" not in code and "O" not in code and "1" not in code and "I" not in code


# ── Classroom creation ──────────────────────────────────────────────────────

async def test_create_classroom_assigns_code_and_color(svc, db):
    result = await svc.create_classroom(
        _teacher_id(db), CreateClassroomRequest(name="Grade 7 Science", subject="Science")
    )
    assert result.name == "Grade 7 Science"
    assert len(result.join_code) == 6
    assert result.color.startswith("#")
    assert result.student_count == 0
    assert result.chapter_count == 0


# ── Chapters ─────────────────────────────────────────────────────────────────

async def test_add_chapter_creates_kb_and_orders(svc, db):
    tid = _teacher_id(db)
    classroom = await svc.create_classroom(tid, CreateClassroomRequest(name="Science"))
    cid = UUID(classroom.id)

    ch1 = await svc.add_chapter(tid, cid, CreateChapterRequest(title="Nutrition in Plants"))
    ch2 = await svc.add_chapter(tid, cid, CreateChapterRequest(title="Nutrition in Animals"))

    assert ch1.knowledge_base_id is not None
    assert ch1.order_index == 0
    assert ch2.order_index == 1
    assert len(db.kbs) == 2  # each chapter got its own knowledge base


async def test_add_chapter_rejects_non_owner(svc, db):
    tid = _teacher_id(db)
    classroom = await svc.create_classroom(tid, CreateClassroomRequest(name="Science"))
    with pytest.raises(AuthorizationError):
        await svc.add_chapter(uuid4(), UUID(classroom.id), CreateChapterRequest(title="X"))


# ── Enrolment ────────────────────────────────────────────────────────────────

async def test_join_by_code_is_idempotent(svc, db):
    tid, sid = _teacher_id(db), _student_id(db)
    classroom = await svc.create_classroom(tid, CreateClassroomRequest(name="Science"))

    await svc.join_by_code(sid, classroom.join_code)
    await svc.join_by_code(sid, classroom.join_code)  # second join must not duplicate

    assert len([e for e in db.enrollments if e.classroom_id == UUID(classroom.id)]) == 1


async def test_join_by_code_unknown_raises(svc, db):
    with pytest.raises(EntityNotFound):
        await svc.join_by_code(_student_id(db), "ZZZZZZ")


async def test_join_code_is_case_insensitive(svc, db):
    tid, sid = _teacher_id(db), _student_id(db)
    classroom = await svc.create_classroom(tid, CreateClassroomRequest(name="Science"))
    result = await svc.join_by_code(sid, classroom.join_code.lower())
    assert result.id == classroom.id


# ── Chapter-scoped access control ────────────────────────────────────────────

async def test_resolve_chapter_kb_requires_enrolment(svc, db):
    tid, sid = _teacher_id(db), _student_id(db)
    classroom = await svc.create_classroom(tid, CreateClassroomRequest(name="Science"))
    chapter = await svc.add_chapter(tid, UUID(classroom.id), CreateChapterRequest(title="Light"))

    # Not enrolled yet → forbidden
    with pytest.raises(AuthorizationError):
        await svc.resolve_chapter_kb_for_student(sid, UUID(chapter.id))

    # After joining → resolves to the chapter's KB
    await svc.join_by_code(sid, classroom.join_code)
    kb_id = await svc.resolve_chapter_kb_for_student(sid, UUID(chapter.id))
    assert str(kb_id) == chapter.knowledge_base_id


async def test_student_sees_only_published_chapters(svc, db):
    tid, sid = _teacher_id(db), _student_id(db)
    classroom = await svc.create_classroom(tid, CreateClassroomRequest(name="Science"))
    ch = await svc.add_chapter(tid, UUID(classroom.id), CreateChapterRequest(title="Draft"))
    await svc.update_chapter(tid, UUID(ch.id), UpdateChapterRequest(is_published=False))
    await svc.join_by_code(sid, classroom.join_code)

    visible = await svc.list_chapters_for_student(sid, UUID(classroom.id))
    assert visible == []
