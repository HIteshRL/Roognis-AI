"""
Tests for Phase-LMS classroom extensions — invitations, co-teachers,
join-approval flow, join-code disable, and soft delete.
"""
from uuid import UUID, uuid4

import pytest

from src.application.services.classroom_service import ClassroomService
from src.domain.entities.classroom import Classroom, Enrollment
from src.domain.entities.user import User
from src.domain.exceptions import AuthorizationError, DuplicateEntity, EntityNotFound


class FakeClassroomRepo:
    def __init__(self):
        self.items: dict[UUID, Classroom] = {}

    async def get_by_id(self, classroom_id):
        return self.items.get(classroom_id)

    async def get_by_join_code(self, join_code):
        return next((c for c in self.items.values() if c.join_code == join_code), None)

    async def list_by_teacher(self, teacher_id, include_archived=False):
        return [
            c for c in self.items.values()
            if c.teacher_id == teacher_id and (include_archived or not c.is_archived)
        ]

    async def update(self, classroom):
        self.items[classroom.id] = classroom
        return classroom

    async def count_students(self, classroom_id):
        return 0

    async def count_chapters(self, classroom_id):
        return 0


class FakeEnrollmentRepo:
    def __init__(self):
        self.items: list[Enrollment] = []
        self.users: dict[UUID, User] = {}

    async def create(self, enrollment):
        self.items.append(enrollment)
        return enrollment

    async def get(self, classroom_id, student_id):
        return next(
            (
                e for e in self.items
                if e.classroom_id == classroom_id and e.student_id == student_id
            ),
            None,
        )

    async def list_students(self, classroom_id, status="active"):
        return [
            self.users[e.student_id]
            for e in self.items
            if e.classroom_id == classroom_id and e.status == status
        ]

    async def is_enrolled(self, classroom_id, student_id):
        e = await self.get(classroom_id, student_id)
        return bool(e and e.status == "active")

    async def set_status(self, classroom_id, student_id, status):
        e = await self.get(classroom_id, student_id)
        if e:
            e.status = status

    async def delete(self, classroom_id, student_id):
        self.items = [
            e for e in self.items
            if not (e.classroom_id == classroom_id and e.student_id == student_id)
        ]


class FakeTeacherRepo:
    def __init__(self):
        self.items = {}

    async def add(self, membership):
        self.items[(membership.classroom_id, membership.teacher_id)] = membership
        return membership

    async def get(self, classroom_id, teacher_id):
        return self.items.get((classroom_id, teacher_id))

    async def list_by_classroom(self, classroom_id):
        return [m for (cid, _), m in self.items.items() if cid == classroom_id]

    async def list_classroom_ids_for_teacher(self, teacher_id):
        return [cid for (cid, tid) in self.items if tid == teacher_id]

    async def remove(self, classroom_id, teacher_id):
        self.items.pop((classroom_id, teacher_id), None)


class FakeInvitationRepo:
    def __init__(self):
        self.items = {}

    async def create(self, invitation):
        self.items[invitation.id] = invitation
        return invitation

    async def get_by_id(self, invitation_id):
        return self.items.get(invitation_id)

    async def get_by_token(self, token):
        return next((i for i in self.items.values() if i.token == token), None)

    async def list_by_classroom(self, classroom_id, status=None):
        return [
            i for i in self.items.values()
            if i.classroom_id == classroom_id and (status is None or i.status == status)
        ]

    async def list_pending_for_email(self, email):
        return [
            i for i in self.items.values()
            if i.email.lower() == email.lower() and i.status == "pending"
        ]

    async def update(self, invitation):
        self.items[invitation.id] = invitation
        return invitation


class FakeUserRepo:
    def __init__(self):
        self.users: dict[UUID, User] = {}

    async def get_by_id(self, user_id):
        return self.users.get(user_id)

    async def get_by_email(self, email):
        return next(
            (u for u in self.users.values() if u.email.lower() == email.lower()), None
        )


class FakeNotifier:
    def __init__(self):
        self.emitted = []

    async def emit(self, user_id, type, title, body="", data=None):
        self.emitted.append({"user_id": user_id, "type": type})

    async def emit_many(self, user_ids, type, title, body="", data=None):
        for uid in user_ids:
            await self.emit(uid, type, title)


@pytest.fixture
def world():
    owner = User(email="owner@x.com", username="owner", password_hash="h", role="teacher")
    co = User(email="co@x.com", username="co", password_hash="h", role="teacher")
    student = User(email="stu@x.com", username="stu", password_hash="h")
    classroom = Classroom(teacher_id=owner.id, name="Math 9")

    classrooms = FakeClassroomRepo()
    classrooms.items[classroom.id] = classroom
    users = FakeUserRepo()
    users.users = {owner.id: owner, co.id: co, student.id: student}
    enrollments = FakeEnrollmentRepo()
    enrollments.users = users.users

    svc = ClassroomService(
        classroom_repo=classrooms,
        chapter_repo=None,
        enrollment_repo=enrollments,
        kb_repo=None,
        user_repo=users,
        doc_repo=None,
        teacher_repo=FakeTeacherRepo(),
        invitation_repo=FakeInvitationRepo(),
        notification_svc=FakeNotifier(),
    )
    return {
        "svc": svc,
        "owner": owner,
        "co": co,
        "student": student,
        "classroom": classroom,
        "enrollments": enrollments,
    }


@pytest.mark.asyncio
async def test_invite_and_accept_co_teacher(world):
    svc = world["svc"]
    invitation = await svc.invite(
        world["owner"].id, world["classroom"].id, world["co"].email, "co_teacher"
    )
    await svc.respond_to_invitation(world["co"].id, UUID(invitation.id), accept=True)
    # Co-teacher can now act on the classroom (e.g. read invitations).
    assert await svc.list_invitations(world["co"].id, world["classroom"].id) is not None


@pytest.mark.asyncio
async def test_invite_and_accept_student_enrolls(world):
    svc = world["svc"]
    invitation = await svc.invite(
        world["owner"].id, world["classroom"].id, world["student"].email, "student"
    )
    await svc.respond_to_invitation(world["student"].id, UUID(invitation.id), accept=True)
    assert await world["enrollments"].is_enrolled(
        world["classroom"].id, world["student"].id
    )


@pytest.mark.asyncio
async def test_wrong_user_cannot_accept_invitation(world):
    svc = world["svc"]
    invitation = await svc.invite(
        world["owner"].id, world["classroom"].id, world["co"].email, "co_teacher"
    )
    with pytest.raises(EntityNotFound):
        await svc.respond_to_invitation(world["student"].id, UUID(invitation.id), accept=True)


@pytest.mark.asyncio
async def test_join_with_approval_flow(world):
    svc = world["svc"]
    world["classroom"].settings = {"require_approval": True}
    await svc.join_by_code(world["student"].id, world["classroom"].join_code)
    # Pending — not yet an active member.
    assert not await world["enrollments"].is_enrolled(
        world["classroom"].id, world["student"].id
    )
    pending = await svc.list_pending_enrollments(world["owner"].id, world["classroom"].id)
    assert len(pending) == 1

    # A second join attempt while pending is rejected.
    with pytest.raises(DuplicateEntity):
        await svc.join_by_code(world["student"].id, world["classroom"].join_code)

    await svc.approve_enrollment(
        world["owner"].id, world["classroom"].id, world["student"].id
    )
    assert await world["enrollments"].is_enrolled(
        world["classroom"].id, world["student"].id
    )


@pytest.mark.asyncio
async def test_reject_enrollment_removes_request(world):
    svc = world["svc"]
    world["classroom"].settings = {"require_approval": True}
    await svc.join_by_code(world["student"].id, world["classroom"].join_code)
    await svc.reject_enrollment(world["owner"].id, world["classroom"].id, world["student"].id)
    assert (
        await world["enrollments"].get(world["classroom"].id, world["student"].id) is None
    )


@pytest.mark.asyncio
async def test_disabled_join_code_blocks_joining(world):
    svc = world["svc"]
    await svc.set_join_code_enabled(world["owner"].id, world["classroom"].id, False)
    with pytest.raises(EntityNotFound):
        await svc.join_by_code(world["student"].id, world["classroom"].join_code)


@pytest.mark.asyncio
async def test_soft_delete_owner_only(world):
    svc = world["svc"]
    with pytest.raises(AuthorizationError):
        await svc.delete_classroom(world["co"].id, world["classroom"].id)
    await svc.delete_classroom(world["owner"].id, world["classroom"].id)
    assert world["classroom"].is_deleted
    # Deleted classrooms disappear from teacher actions.
    with pytest.raises(EntityNotFound):
        await svc.get_classroom_for_teacher(world["owner"].id, world["classroom"].id)


@pytest.mark.asyncio
async def test_leave_classroom(world):
    svc = world["svc"]
    await svc.join_by_code(world["student"].id, world["classroom"].join_code)
    await svc.leave_classroom(world["student"].id, world["classroom"].id)
    assert not await world["enrollments"].is_enrolled(
        world["classroom"].id, world["student"].id
    )


@pytest.mark.asyncio
async def test_leave_without_enrollment_raises(world):
    with pytest.raises(EntityNotFound):
        await world["svc"].leave_classroom(uuid4(), world["classroom"].id)
