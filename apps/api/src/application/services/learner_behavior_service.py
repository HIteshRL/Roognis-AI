"""
Phase 0.3: Learner Behavior Analyzer.

Mines session history to compute behavioral signals — the patterns that tell
the LLM *how* this student learns, not just *what* they know. Runs in the
orchestrator pipeline after each session.

Signals are stored as JSONB on student_profiles and fed into the
LearnerContextService for prompt injection.
"""
from collections import Counter
from datetime import UTC, datetime, timedelta
from uuid import UUID

import structlog

from src.domain.entities.learning import BLOOM_LEVELS, BehavioralSignals
from src.domain.repositories.learning_repository import (
    AbstractLearningGapRepository,
    AbstractLearningSessionRepository,
    AbstractMasteryRepository,
)

logger = structlog.get_logger(__name__)

_ANALYSIS_WINDOW_DAYS = 30
_TREND_WINDOW = 10
_STREAK_LOOKBACK_DAYS = 60


class LearnerBehaviorService:
    def __init__(
        self,
        session_repo: AbstractLearningSessionRepository,
        mastery_repo: AbstractMasteryRepository,
        gap_repo: AbstractLearningGapRepository,
    ) -> None:
        self._sessions = session_repo
        self._mastery = mastery_repo
        self._gaps = gap_repo

    async def compute(self, user_id: UUID) -> BehavioralSignals:
        now = datetime.now(UTC)
        since = now - timedelta(days=_ANALYSIS_WINDOW_DAYS)
        sessions = await self._sessions.list_since(user_id, since)
        mastery_records = await self._mastery.list_by_user(user_id)
        gaps = await self._gaps.list_by_user(user_id, include_resolved=True)

        total_all_time = await self._sessions.count_by_user(user_id)

        signals = BehavioralSignals(last_computed=now.isoformat())
        signals.total_sessions = total_all_time

        if not sessions:
            return signals

        # ── Bloom distribution → preferred and struggle levels ───────────
        bloom_counts: Counter[str] = Counter()
        misconception_blooms: Counter[str] = Counter()
        for s in sessions:
            bloom_counts[s.bloom_level] += 1
            if s.misconceptions:
                misconception_blooms[s.bloom_level] += len(s.misconceptions)

        if bloom_counts:
            signals.preferred_bloom_level = bloom_counts.most_common(1)[0][0]
        if misconception_blooms:
            signals.struggle_bloom_level = misconception_blooms.most_common(1)[0][0]

        # ── Session duration ─────────────────────────────────────────────
        durations = [s.duration_ms for s in sessions if s.duration_ms > 0]
        if durations:
            signals.avg_session_duration_ms = round(sum(durations) / len(durations))

        # ── Frequency ────────────────────────────────────────────────────
        window_days = min(_ANALYSIS_WINDOW_DAYS, max(1, (now - sessions[-1].created_at).days + 1))
        signals.sessions_per_day = round(len(sessions) / window_days, 2)

        # ── Complexity trend ─────────────────────────────────────────────
        signals.question_complexity_trend = self._compute_complexity_trend(sessions)

        # ── Subject distribution ─────────────────────────────────────────
        subject_counts: Counter[str] = Counter()
        for s in sessions:
            if s.subject:
                subject_counts[s.subject] += 1
        if subject_counts:
            signals.dominant_subject = subject_counts.most_common(1)[0][0]

        # ── Misconception total ──────────────────────────────────────────
        signals.total_misconceptions = sum(
            1 for g in gaps if not g.is_resolved
        )

        # ── Engagement streak ────────────────────────────────────────────
        signals.engagement_streak = self._compute_streak(sessions, now)

        # ── Strengths ────────────────────────────────────────────────────
        mastered = sorted(
            [r for r in mastery_records if r.score >= 85],
            key=lambda r: -r.score,
        )
        signals.strengths = [r.concept_name for r in mastered[:5]]

        # ── Recent topics ────────────────────────────────────────────────
        seen: set[str] = set()
        recent: list[str] = []
        for s in sessions:
            if s.primary_concept and s.primary_concept not in seen:
                seen.add(s.primary_concept)
                recent.append(s.primary_concept)
                if len(recent) >= 5:
                    break
        signals.recent_topics = recent

        # ── Response pattern (conceptual vs procedural) ──────────────────
        signals.response_pattern = self._detect_response_pattern(sessions)

        logger.debug(
            "behavioral_signals_computed",
            user_id=str(user_id),
            sessions_analyzed=len(sessions),
            preferred_bloom=signals.preferred_bloom_level,
            streak=signals.engagement_streak,
        )
        return signals

    @staticmethod
    def _compute_complexity_trend(sessions: list) -> str:
        if len(sessions) < 4:
            return "stable"

        bloom_rank = {level: i for i, level in enumerate(BLOOM_LEVELS)}
        ranked = [bloom_rank.get(s.bloom_level, 1) for s in sessions]

        half = len(ranked) // 2
        recent_avg = sum(ranked[:half]) / half
        earlier_avg = sum(ranked[half:]) / (len(ranked) - half)
        diff = recent_avg - earlier_avg

        if diff >= 0.5:
            return "rising"
        if diff <= -0.5:
            return "declining"
        return "stable"

    @staticmethod
    def _compute_streak(sessions: list, now: datetime) -> int:
        if not sessions:
            return 0

        active_dates: set[str] = set()
        for s in sessions:
            active_dates.add(s.created_at.strftime("%Y-%m-%d"))

        streak = 0
        day = now.date()
        today_str = day.strftime("%Y-%m-%d")
        if today_str not in active_dates:
            day -= timedelta(days=1)

        for _ in range(_STREAK_LOOKBACK_DAYS):
            if day.strftime("%Y-%m-%d") in active_dates:
                streak += 1
                day -= timedelta(days=1)
            else:
                break
        return streak

    @staticmethod
    def _detect_response_pattern(sessions: list) -> str:
        if len(sessions) < 3:
            return "unknown"

        bloom_rank = {level: i for i, level in enumerate(BLOOM_LEVELS)}

        procedural_count = 0
        conceptual_count = 0
        for s in sessions:
            rank = bloom_rank.get(s.bloom_level, 1)
            if rank <= 2:
                procedural_count += 1
            else:
                conceptual_count += 1

        total = procedural_count + conceptual_count
        if not total:
            return "unknown"
        procedural_ratio = procedural_count / total

        if procedural_ratio >= 0.65:
            return "procedural"
        if procedural_ratio <= 0.35:
            return "conceptual"
        return "mixed"
