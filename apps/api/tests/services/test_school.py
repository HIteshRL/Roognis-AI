"""Unit tests for Phase 0.8 — school / classroom / syllabus services (in-memory)."""
from uuid import uuid4

import pytest

from src.application.services.classroom_service import ClassroomService
from src.application.services.school_service import SchoolService
from src.application.services.syllabus_service import SyllabusService
from src.domain.entities.school import Role
from src.domain.entities.user import User
from src.domain.exceptions import (
    AuthorizationError,
    DuplicateEntity,
    EntityNotFound,
)

# ── Fakes ────────────────────────────────────────────────────────────────────


class _FakeUserRepo:
    def __init__(self):
        self.rows: dict[str, User] = {}

    def add(self, user: User) -> User:
        self.rows[str(user.id)] = user
        return user

    async def get_by_id(self, user_id):
        return self.rows.get(str(user_id))

    async def get_by_email(self, email):
        return next((u for u in self.rows.values() if u.email == email), None)

    async def get_by_username(self, username):
        return next((u for u in self.rows.values() if u.username == username), None)

    async def get_by_clerk_id(self, clerk_id):
        return None

    async def create(self, user):
        return self.add(user)

    async def update(self, user):
        self.rows[str(user.id)] = user
        return user

    async def delete(self, user_id):
        self.rows.pop(str(user_id), None)


class _FakeSchoolRepo:
    def __init__(self):
        self.rows = {}

    async def create(self, school):
        self.rows[str(school.id)] = school
        return school

    async def get_by_id(self, school_id):
        return self.rows.get(str(school_id))

    async def get_by_slug(self, slug):
        return next((s for s in self.rows.values() if s.slug == slug), None)

    async def list_for_member(self, user_id):
        return list(self.rows.values())


class _FakeMemberRepo:
    def __init__(self):
        self.rows = []

    async def create(self, member):
        self.rows.append(member)
        return member

    async def get(self, school_id, user_id):
        return next(
            (m for m in self.rows if m.school_id == school_id and m.user_id == user_id),
            None,
        )

    async def list_by_school(self, school_id):
        return [m for m in self.rows if m.school_id == school_id]


class _FakeClassroomRepo:
    def __init__(self):
        self.rows = {}

    async def create(self, classroom):
        self.rows[str(classroom.id)] = classroom
        return classroom

    async def get_by_id(self, classroom_id):
        return self.rows.get(str(classroom_id))

    async def get_by_join_code(self, join_code):
        return next((c for c in self.rows.values() if c.join_code == join_code), None)

    async def list_by_teacher(self, teacher_id):
        return [c for c in self.rows.values() if c.teacher_id == teacher_id]

    async def list_by_school(self, school_id):
        return [c for c in self.rows.values() if c.school_id == school_id]

    async def list_by_ids(self, classroom_ids):
        ids = {str(c) for c in classroom_ids}
        return [c for c in self.rows.values() if str(c.id) in ids]

    async def update(self, classroom):
        self.rows[str(classroom.id)] = classroom
        return classroom

    async def delete(self, classroom_id):
        self.rows.pop(str(classroom_id), None)


class _FakeEnrollmentRepo:
    def __init__(self):
        self.rows = []

    async def create(self, enrollment):
        self.rows.append(enrollment)
        return enrollment

    async def get(self, classroom_id, student_id):
        return next(
            (
                e
                for e in self.rows
                if e.classroom_id == classroom_id and e.student_id == student_id
            ),
            None,
        )

    async def list_by_classroom(self, classroom_id):
        return [e for e in self.rows if e.classroom_id == classroom_id]

    async def list_by_student(self, student_id):
        return [
            e
            for e in self.rows
            if e.student_id == student_id and e.status == "active"
        ]

    async def update(self, enrollment):
        return enrollment

    async def count_by_classroom(self, classroom_id):
        return len(
            [
                e
                for e in self.rows
                if e.classroom_id == classroom_id and e.status == "active"
            ]
        )


class _FakeSyllabusRepo:
    def __init__(self):
        self.rows = {}

    async def create(self, item):
        self.rows[str(item.id)] = item
        return item

    async def get_by_id(self, item_id):
        return self.rows.get(str(item_id))

    async def list_by_classroom(self, classroom_id, published_only=False):
        items = [i for i in self.rows.values() if i.classroom_id == classroom_id]
        if published_only:
            items = [i for i in items if i.is_published]
        return sorted(items, key=lambda i: i.order_index)

    async def update(self, item):
        self.rows[str(item.id)] = item
        return item

    async def delete(self, item_id):
        self.rows.pop(str(item_id), None)


# ── Fixtures ─────────────────────────────────────────────────────────────────


def _user(role=Role.STUDENT, **kw):
    n = uuid4().hex[:8]
    return User(
        email=kw.get("email", f"{n}@x.io"),
        username=kw.get("username", n),
        password_hash="x",
        role=role,
    )


@pytest.fixture
def users():
    return _FakeUserRepo()


@pytest.fixture
def school_svc(users):
    return SchoolService(_FakeSchoolRepo(), _FakeMemberRepo(), users)


def _classroom_svc(users, members, classrooms, enrollments, syllabus):
    return ClassroomService(classrooms, enrollments, members, syllabus, users, 6)


# ── School ───────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_school_promotes_owner(users):
    owner = users.add(_user(Role.STUDENT))
    svc = SchoolService(_FakeSchoolRepo(), _FakeMemberRepo(), users)

    school, role = await svc.create_school(owner.id, "Green Valley High", None)

    assert role == Role.SCHOOL_ADMIN
    assert school.slug == "green-valley-high"
    assert users.rows[str(owner.id)].role == Role.SCHOOL_ADMIN
    assert await svc.get_role(school.id, owner.id) == Role.SCHOOL_ADMIN


@pytest.mark.asyncio
async def test_add_teacher_requires_admin(users):
    members = _FakeMemberRepo()
    svc = SchoolService(_FakeSchoolRepo(), members, users)
    owner = users.add(_user())
    school, _ = await svc.create_school(owner.id, "Riverdale", None)

    teacher_user = users.add(_user(email="t@x.io"))
    member, email, username = await svc.add_teacher(
        school.id, owner.id, "t@x.io", Role.TEACHER
    )
    assert member.role == Role.TEACHER
    assert users.rows[str(teacher_user.id)].role == Role.TEACHER

    outsider = users.add(_user())
    with pytest.raises(AuthorizationError):
        await svc.add_teacher(school.id, outsider.id, "t@x.io", Role.TEACHER)


@pytest.mark.asyncio
async def test_add_teacher_duplicate_and_missing(users):
    svc = SchoolService(_FakeSchoolRepo(), _FakeMemberRepo(), users)
    owner = users.add(_user())
    school, _ = await svc.create_school(owner.id, "Oak", None)
    users.add(_user(email="t@x.io"))

    await svc.add_teacher(school.id, owner.id, "t@x.io", Role.TEACHER)
    with pytest.raises(DuplicateEntity):
        await svc.add_teacher(school.id, owner.id, "t@x.io", Role.TEACHER)
    with pytest.raises(EntityNotFound):
        await svc.add_teacher(school.id, owner.id, "ghost@x.io", Role.TEACHER)


# ── Classroom ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_classroom_and_join(users):
    members = _FakeMemberRepo()
    schools = _FakeSchoolRepo()
    school_svc = SchoolService(schools, members, users)
    owner = users.add(_user())
    school, _ = await school_svc.create_school(owner.id, "Delta", None)

    classrooms, enrollments, syllabus = (
        _FakeClassroomRepo(),
        _FakeEnrollmentRepo(),
        _FakeSyllabusRepo(),
    )
    svc = _classroom_svc(users, members, classrooms, enrollments, syllabus)

    classroom = await svc.create_classroom(
        owner.id, school.id, "Physics 10", "Physics", "10", None
    )
    assert classroom.join_code
    assert len(classroom.join_code) == 6

    student = users.add(_user())
    joined = await svc.join_by_code(student.id, classroom.join_code.lower())
    assert joined.id == classroom.id
    # idempotent
    await svc.join_by_code(student.id, classroom.join_code)
    students, _ = await svc.counts(classroom.id)
    assert students == 1


@pytest.mark.asyncio
async def test_create_classroom_non_member_rejected(users):
    members = _FakeMemberRepo()
    classrooms, enrollments, syllabus = (
        _FakeClassroomRepo(),
        _FakeEnrollmentRepo(),
        _FakeSyllabusRepo(),
    )
    svc = _classroom_svc(users, members, classrooms, enrollments, syllabus)
    stranger = users.add(_user(Role.TEACHER))
    with pytest.raises(AuthorizationError):
        await svc.create_classroom(stranger.id, uuid4(), "X", None, None, None)


@pytest.mark.asyncio
async def test_join_bad_code(users):
    svc = _classroom_svc(
        users,
        _FakeMemberRepo(),
        _FakeClassroomRepo(),
        _FakeEnrollmentRepo(),
        _FakeSyllabusRepo(),
    )
    student = users.add(_user())
    with pytest.raises(EntityNotFound):
        await svc.join_by_code(student.id, "ZZZZZZ")


@pytest.mark.asyncio
async def test_roster_and_manage_auth(users):
    members = _FakeMemberRepo()
    schools = _FakeSchoolRepo()
    school_svc = SchoolService(schools, members, users)
    owner = users.add(_user())
    school, _ = await school_svc.create_school(owner.id, "Echo", None)

    classrooms, enrollments, syllabus = (
        _FakeClassroomRepo(),
        _FakeEnrollmentRepo(),
        _FakeSyllabusRepo(),
    )
    svc = _classroom_svc(users, members, classrooms, enrollments, syllabus)
    classroom = await svc.create_classroom(owner.id, school.id, "Bio", None, None, None)
    student = users.add(_user(username="alice", email="alice@x.io"))
    await svc.join_by_code(student.id, classroom.join_code)

    roster = await svc.roster(classroom.id, owner.id)
    assert len(roster) == 1
    assert roster[0][1] == "alice"

    intruder = users.add(_user(Role.TEACHER))
    with pytest.raises(AuthorizationError):
        await svc.roster(classroom.id, intruder.id)


# ── Syllabus ─────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_syllabus_publish_visibility(users):
    members = _FakeMemberRepo()
    schools = _FakeSchoolRepo()
    school_svc = SchoolService(schools, members, users)
    owner = users.add(_user())
    school, _ = await school_svc.create_school(owner.id, "Foxtrot", None)

    classrooms, enrollments, syllabus = (
        _FakeClassroomRepo(),
        _FakeEnrollmentRepo(),
        _FakeSyllabusRepo(),
    )
    classroom_svc = _classroom_svc(users, members, classrooms, enrollments, syllabus)
    classroom = await classroom_svc.create_classroom(
        owner.id, school.id, "Chem", None, None, None
    )

    syl_svc = SyllabusService(syllabus, classrooms, members, enrollments)
    draft = await syl_svc.add_item(
        classroom.id, owner.id, "Chem", "Atoms", None, None, 0, None, False
    )
    await syl_svc.add_item(
        classroom.id, owner.id, "Chem", "Bonds", None, None, 1, None, True
    )

    # teacher sees all
    teacher_view = await syl_svc.list_items(classroom.id, owner.id)
    assert len(teacher_view) == 2

    # unenrolled student blocked
    student = users.add(_user())
    with pytest.raises(AuthorizationError):
        await syl_svc.list_items(classroom.id, student.id)

    # enrolled student sees only published
    await classroom_svc.join_by_code(student.id, classroom.join_code)
    student_view = await syl_svc.list_items(classroom.id, student.id)
    assert len(student_view) == 1
    assert student_view[0].chapter == "Bonds"

    # publish the draft, now visible
    await syl_svc.update_item(draft.id, owner.id, is_published=True)
    assert len(await syl_svc.list_items(classroom.id, student.id)) == 2


@pytest.mark.asyncio
async def test_syllabus_manage_auth(users):
    members = _FakeMemberRepo()
    schools = _FakeSchoolRepo()
    school_svc = SchoolService(schools, members, users)
    owner = users.add(_user())
    school, _ = await school_svc.create_school(owner.id, "Golf", None)
    classrooms, enrollments, syllabus = (
        _FakeClassroomRepo(),
        _FakeEnrollmentRepo(),
        _FakeSyllabusRepo(),
    )
    classroom_svc = _classroom_svc(users, members, classrooms, enrollments, syllabus)
    classroom = await classroom_svc.create_classroom(
        owner.id, school.id, "Math", None, None, None
    )
    syl_svc = SyllabusService(syllabus, classrooms, members, enrollments)

    intruder = users.add(_user(Role.TEACHER))
    with pytest.raises(AuthorizationError):
        await syl_svc.add_item(
            classroom.id, intruder.id, "Math", "X", None, None, 0, None, False
        )
