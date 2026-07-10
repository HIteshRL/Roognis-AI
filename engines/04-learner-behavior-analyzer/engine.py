"""
Learner Behavior Analyzer — Roognis AI (Phase 0.3)

Mines session history to compute behavioral signals — the patterns that tell
the LLM *how* this student learns, not just *what* they know.

Signals stored on student_profiles (JSONB) and injected into the LLM system
prompt via LearnerContextService.
"""
from collections import Counter
from datetime import UTC, datetime, timedelta
from uuid import UUID

import structlog

from domain import (
    BLOOM_LEVELS,
    AbstractLearningGapRepository,
    AbstractLearningSessionRepository,
    AbstractMasteryRepository,
    BehavioralSignals,
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

        durations = [s.duration_ms for s in sessions if s.duration_ms > 0]
        if durations:
            signals.avg_session_duration_ms = round(sum(durations) / len(durations))

        window_days = min(_ANALYSIS_WINDOW_DAYS, max(1, (now - sessions[-1].created_at).days + 1))
        signals.sessions_per_day = round(len(sessions) / window_days, 2)
        signals.question_complexity_trend = self._compute_complexity_trend(sessions)

        subject_counts: Counter[str] = Counter(s.subject for s in sessions if s.subject)
        if subject_counts:
            signals.dominant_subject = subject_counts.most_common(1)[0][0]

        signals.total_misconceptions = sum(1 for g in gaps if not g.is_resolved)
        signals.engagement_streak = self._compute_streak(sessions, now)

        mastered = sorted([r for r in mastery_records if r.score >= 85], key=lambda r: -r.score)
        signals.strengths = [r.concept_name for r in mastered[:5]]

        seen: set[str] = set()
        recent: list[str] = []
        for s in sessions:
            if s.primary_concept and s.primary_concept not in seen:
                seen.add(s.primary_concept)
                recent.append(s.primary_concept)
                if len(recent) >= 5:
                    break
        signals.recent_topics = recent
        signals.response_pattern = self._detect_response_pattern(sessions)

        logger.debug("behavioral_signals_computed", user_id=str(user_id),
                     sessions_analyzed=len(sessions), preferred_bloom=signals.preferred_bloom_level,
                     streak=signals.engagement_streak)
        return signals

    @staticmethod
    def _compute_complexity_trend(sessions: list) -> str:
        if len(sessions) < 4:
            return "stable"
        bloom_rank = {level: i for i, level in enumerate(BLOOM_LEVELS)}
        ranked = [bloom_rank.get(s.bloom_level, 1) for s in sessions]
        half = len(ranked) // 2
        diff = sum(ranked[:half]) / half - sum(ranked[half:]) / (len(ranked) - half)
        if diff >= 0.5: return "rising"
        if diff <= -0.5: return "declining"
        return "stable"

    @staticmethod
    def _compute_streak(sessions: list, now: datetime) -> int:
        if not sessions:
            return 0
        active_dates: set[str] = {s.created_at.strftime("%Y-%m-%d") for s in sessions}
        streak = 0
        day = now.date()
        if day.strftime("%Y-%m-%d") not in active_dates:
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
        procedural = sum(1 for s in sessions if bloom_rank.get(s.bloom_level, 1) <= 2)
        total = len(sessions)
        ratio = procedural / total
        if ratio >= 0.65: return "procedural"
        if ratio <= 0.35: return "conceptual"
        return "mixed"
