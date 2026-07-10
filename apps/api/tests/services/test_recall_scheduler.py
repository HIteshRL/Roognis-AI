"""Tests for RecallScheduler over an in-memory schedule repository."""
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from src.application.services.recall_scheduler import RecallScheduler, quality_from_signal
from tests.fakes import FakeRecallScheduleRepository

T0 = datetime(2026, 1, 1, tzinfo=UTC)


def test_quality_from_signal_mapping():
    assert quality_from_signal("correct") == 5
    assert quality_from_signal("partial") == 3
    assert quality_from_signal("misconception") == 0
    assert quality_from_signal("something_else") == 3


async def test_record_review_persists_and_schedules():
    repo = FakeRecallScheduleRepository()
    scheduler = RecallScheduler(schedule_repo=repo)
    user, concept = uuid4(), uuid4()

    schedule = await scheduler.record_review(user, concept, "Fractions", quality=5, now=T0)
    assert schedule.repetitions == 1
    assert schedule.next_review_at == T0 + timedelta(days=1)

    # persisted
    stored = await repo.get_by_concept(user, concept)
    assert stored.repetitions == 1


async def test_due_returns_only_past_due():
    repo = FakeRecallScheduleRepository()
    scheduler = RecallScheduler(schedule_repo=repo)
    user, concept = uuid4(), uuid4()
    await scheduler.record_review(user, concept, "Fractions", quality=5, now=T0)

    assert await scheduler.due(user, now=T0 + timedelta(hours=1)) == []
    due = await scheduler.due(user, now=T0 + timedelta(days=2))
    assert len(due) == 1


async def test_at_risk_flags_decayed_retention():
    repo = FakeRecallScheduleRepository()
    scheduler = RecallScheduler(schedule_repo=repo)
    user, concept = uuid4(), uuid4()
    await scheduler.record_review(user, concept, "Fractions", quality=5, now=T0)

    risky = await scheduler.at_risk(user, threshold=0.6, now=T0 + timedelta(days=3))
    assert len(risky) == 1
    _schedule, retention = risky[0]
    assert retention < 0.6


async def test_record_signal_uses_quality_mapping():
    repo = FakeRecallScheduleRepository()
    scheduler = RecallScheduler(schedule_repo=repo)
    user, concept = uuid4(), uuid4()
    schedule = await scheduler.record_signal(user, concept, "Fractions", "misconception", now=T0)
    # quality 0 → failure path → interval reset to 1, one lapse
    assert schedule.lapses == 1
    assert schedule.interval_days == 1
