"""Unit tests for Teacher Dashboard analytics (in-memory fakes).

Auth enforcement lives in ClassroomService.roster (covered by test_school.py);
here we fake roster() and focus on the aggregation + rollup logic, including
that auth errors propagate rather than being swallowed.
"""
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from src.application.services.classroom_analytics_service import ClassroomAnalyticsService
from src.domain.entities.school import Enrollment
from src.domain.exceptions import AuthorizationError, EntityNotFound

_NOW = datetime(2026, 7, 1, tzinfo=UTC)


class _FakeClassroomService:
    def __init__(self, rows=None, error=None):
        self._rows = rows or []
        self._error = error

    async def roster(self, classroom_id, user_id):
        if self._error:
            raise self._error
        return self._rows


class _FakeMasteryRepo:
    def __init__(self, avg_by):
        self._avg = avg_by

    async def average_scores_by_users(self, ids):
        return {u: self._avg[u] for u in ids if u in self._avg}


class _FakeGapRepo:
    def __init__(self, counts, top):
        self._counts = counts
        self._top = top

    async def active_gap_counts_by_users(self, ids):
        return {u: self._counts[u] for u in ids if u in self._counts}

    async def top_concepts_by_users(self, ids, limit=5):
        return self._top[:limit]


class _FakeSessionRepo:
    def __init__(self, stats):
        self._stats = stats

    async def session_stats_by_users(self, ids):
        return {u: self._stats[u] for u in ids if u in self._stats}


def _roster(*students):
    """students: (username, email, status) → (Enrollment, username, email) rows + ids."""
    rows, ids = [], []
    for username, email, status in students:
        sid = uuid4()
        rows.append((Enrollment(classroom_id=uuid4(), student_id=sid, status=status), username, email))
        ids.append(sid)
    return rows, ids


def _svc(rows, avg=None, gaps=None, top=None, stats=None, error=None):
    return ClassroomAnalyticsService(
        classroom_service=_FakeClassroomService(rows, error),
        mastery_repo=_FakeMasteryRepo(avg or {}),
        gap_repo=_FakeGapRepo(gaps or {}, top or []),
        session_repo=_FakeSessionRepo(stats or {}),
    )


@pytest.mark.asyncio
async def test_per_student_and_class_rollups():
    rows, ids = _roster(("alice", "a@x.io", "active"), ("bob", "b@x.io", "active"))
    a, b = ids
    svc = _svc(
        rows,
        avg={a: 82.0, b: 40.0},
        gaps={a: 1, b: 3},
        top=[("Fractions", 2), ("Decimals", 1)],
        stats={a: (10, _NOW), b: (4, _NOW)},
    )
    res = await svc.classroom_analytics(uuid4(), uuid4())

    assert res.student_count == 2
    assert res.total_sessions == 14
    assert res.class_avg_mastery == 61.0
    alice = next(s for s in res.students if s.username == "alice")
    assert alice.avg_mastery == 82.0 and alice.active_gap_count == 1 and alice.session_count == 10
    assert res.top_misconceptions[0].concept_name == "Fractions"
    assert res.top_misconceptions[0].student_count == 2


@pytest.mark.asyncio
async def test_auth_error_propagates():
    with pytest.raises(AuthorizationError):
        await _svc([], error=AuthorizationError("nope")).classroom_analytics(uuid4(), uuid4())


@pytest.mark.asyncio
async def test_unknown_classroom_propagates():
    with pytest.raises(EntityNotFound):
        await _svc([], error=EntityNotFound("gone")).classroom_analytics(uuid4(), uuid4())


@pytest.mark.asyncio
async def test_empty_roster_returns_zeros():
    res = await _svc([]).classroom_analytics(uuid4(), uuid4())
    assert res.student_count == 0
    assert res.total_sessions == 0
    assert res.class_avg_mastery == 0.0
    assert res.top_misconceptions == []
    assert {b.label for b in res.mastery_distribution} == {
        "struggling", "developing", "proficient", "mastered", "no_data"
    }
    assert all(b.count == 0 for b in res.mastery_distribution)


@pytest.mark.asyncio
async def test_student_with_no_learning_data_defaults():
    rows, ids = _roster(("newbie", "n@x.io", "active"))
    res = await _svc(rows).classroom_analytics(uuid4(), uuid4())
    s = res.students[0]
    assert s.avg_mastery == 0.0
    assert s.active_gap_count == 0
    assert s.session_count == 0
    assert s.last_activity is None
    no_data = next(b for b in res.mastery_distribution if b.label == "no_data")
    assert no_data.count == 1


@pytest.mark.asyncio
async def test_mastery_distribution_buckets():
    rows, ids = _roster(
        ("s1", "1@x.io", "active"), ("s2", "2@x.io", "active"),
        ("s3", "3@x.io", "active"), ("s4", "4@x.io", "active"),
    )
    a, b, c, d = ids
    res = await _svc(rows, avg={a: 20.0, b: 45.0, c: 70.0, d: 90.0}).classroom_analytics(uuid4(), uuid4())
    dist = {x.label: x.count for x in res.mastery_distribution}
    assert dist["struggling"] == 1
    assert dist["developing"] == 1
    assert dist["proficient"] == 1
    assert dist["mastered"] == 1


@pytest.mark.asyncio
async def test_top_misconceptions_limit_respected():
    rows, ids = _roster(("x", "x@x.io", "active"))
    top = [(f"C{i}", 10 - i) for i in range(8)]
    res = await _svc(rows, top=top).classroom_analytics(uuid4(), uuid4())
    # the service passes limit=5 to the repo; our fake honors it
    assert len(res.top_misconceptions) == 5
    assert res.top_misconceptions[0].concept_name == "C0"


@pytest.mark.asyncio
async def test_inactive_enrollment_excluded():
    rows, ids = _roster(("active_kid", "a@x.io", "active"), ("removed_kid", "r@x.io", "removed"))
    res = await _svc(rows).classroom_analytics(uuid4(), uuid4())
    assert res.student_count == 1
    assert [s.username for s in res.students] == ["active_kid"]
