"""Unit tests for the Parent Portal (ADR-013) — in-memory fakes."""
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

from src.application.services.parent_service import ParentService
from src.domain.entities.school import Role
from src.domain.entities.user import User
from src.domain.exceptions import (
    AuthorizationError,
    EntityNotFound,
    ValidationError,
)


class _FakeRedis:
    def __init__(self):
        self.kv = {}

    async def get(self, key):
        return self.kv.get(key)

    async def set(self, key, value, ex=None):
        self.kv[key] = value


class _FakeUserRepo:
    def __init__(self):
        self.rows = {}

    def add(self, u):
        self.rows[str(u.id)] = u
        return u

    async def get_by_id(self, uid):
        return self.rows.get(str(uid))

    async def update(self, u):
        self.rows[str(u.id)] = u
        return u


class _FakeGuardianRepo:
    def __init__(self):
        self.rows = []

    async def create(self, link):
        self.rows.append(link)
        return link

    async def get(self, parent_id, student_id):
        return next(
            (
                x
                for x in self.rows
                if x.parent_id == parent_id and x.student_id == student_id
            ),
            None,
        )

    async def list_by_parent(self, parent_id):
        return [x for x in self.rows if x.parent_id == parent_id and x.status == "active"]

    async def list_by_student(self, student_id):
        return [x for x in self.rows if x.student_id == student_id and x.status == "active"]

    async def update(self, link):
        return link


class _FakeProfileRepo:
    async def get_by_user_id(self, uid):
        return SimpleNamespace(
            grade="8", institution="X", behavioral_signals={"engagement_streak": 4}
        )


class _FakeMasteryRepo:
    async def list_by_user(self, uid):
        return [
            SimpleNamespace(concept_name="Fractions", score=85.0, label="mastered"),
            SimpleNamespace(concept_name="Decimals", score=40.0, label="developing"),
        ]


class _FakeGapRepo:
    async def list_by_user(self, uid, include_resolved=False):
        return [
            SimpleNamespace(concept_name="Long Division", severity="high", is_resolved=False)
        ]


class _FakeSessionRepo:
    async def count_by_user(self, uid):
        return 12

    async def recent_concepts(self, uid, days):
        return ["Fractions"]

    async def list_by_user(self, uid, limit, offset):
        return [
            SimpleNamespace(
                question="What is 1/2 + 1/4?",
                subject="Math",
                created_at=datetime(2026, 7, 1, tzinfo=UTC),
                bloom_level="Apply",
                primary_concept="Fractions",
            )
        ]


def _student():
    n = uuid4().hex[:8]
    return User(email=f"{n}@s.io", username=f"stu_{n}", password_hash="x", role=Role.STUDENT)


def _parent():
    n = uuid4().hex[:8]
    return User(email=f"{n}@p.io", username=f"par_{n}", password_hash="x", role=Role.STUDENT)


def _service(users, guardians, redis):
    return ParentService(
        guardian_repo=guardians,
        user_repo=users,
        profile_repo=_FakeProfileRepo(),
        mastery_repo=_FakeMasteryRepo(),
        gap_repo=_FakeGapRepo(),
        session_repo=_FakeSessionRepo(),
        redis=redis,
    )


@pytest.mark.asyncio
async def test_link_flow_and_children():
    users, guardians, redis = _FakeUserRepo(), _FakeGuardianRepo(), _FakeRedis()
    student = users.add(_student())
    parent = users.add(_parent())
    svc = _service(users, guardians, redis)

    code, ttl = await svc.generate_link_code(student.id)
    assert len(code) == 8 and ttl > 0

    sid, uname = await svc.link_by_code(parent.id, code.lower())
    assert sid == student.id
    assert users.rows[str(parent.id)].role == Role.PARENT

    children = await svc.list_children(parent.id)
    assert len(children) == 1
    assert children[0][3] == "8"  # grade


@pytest.mark.asyncio
async def test_link_invalid_and_self():
    users, guardians, redis = _FakeUserRepo(), _FakeGuardianRepo(), _FakeRedis()
    student = users.add(_student())
    parent = users.add(_parent())
    svc = _service(users, guardians, redis)

    with pytest.raises(EntityNotFound):
        await svc.link_by_code(parent.id, "BADCODE1")

    code, _ = await svc.generate_link_code(student.id)
    with pytest.raises(ValidationError):
        await svc.link_by_code(student.id, code)  # linking to self


@pytest.mark.asyncio
async def test_overview_requires_link_then_revoke():
    users, guardians, redis = _FakeUserRepo(), _FakeGuardianRepo(), _FakeRedis()
    student = users.add(_student())
    parent = users.add(_parent())
    svc = _service(users, guardians, redis)

    with pytest.raises(AuthorizationError):
        await svc.child_overview(parent.id, student.id)

    code, _ = await svc.generate_link_code(student.id)
    await svc.link_by_code(parent.id, code)

    overview = await svc.child_overview(parent.id, student.id)
    assert overview["average_mastery"] > 0
    assert overview["strengths"] == ["Fractions"]
    assert overview["weak_areas"][0]["concept"] == "Long Division"
    assert overview["engagement_streak"] == 4

    await svc.revoke_guardian(student.id, parent.id)
    with pytest.raises(AuthorizationError):
        await svc.child_overview(parent.id, student.id)


@pytest.mark.asyncio
async def test_generate_code_no_redis_fails_open():
    users, guardians = _FakeUserRepo(), _FakeGuardianRepo()
    student = users.add(_student())
    svc = _service(users, guardians, redis=None)
    with pytest.raises(ValidationError):
        await svc.generate_link_code(student.id)
