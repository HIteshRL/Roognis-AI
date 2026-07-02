"""
Phase 0.3: Learner Context Builder.

Transforms the student's profile, mastery state, behavioral signals, and
active gaps into a rich pedagogical instruction block for the LLM system
prompt. The LLM receives actionable adaptation guidance — not just a data
dump, but *how* to teach this specific student.

Never blocks or fails the chat flow — returns None on any missing data.
"""
from uuid import UUID

import structlog

from src.domain.entities.learning import BLOOM_LEVELS, BehavioralSignals
from src.domain.repositories.learning_repository import (
    AbstractLearningGapRepository,
    AbstractMasteryRepository,
    AbstractStudentProfileRepository,
)

logger = structlog.get_logger(__name__)

_MAX_WEAK_CONCEPTS = 5
_MAX_ACTIVE_GAPS = 5
_MAX_STRENGTHS = 3


class LearnerContextService:
    """
    Reads StudentProfile (including behavioral_signals), weakest mastery
    records, and active learning gaps, then renders a structured context
    block with explicit adaptation instructions for the LLM.
    """

    def __init__(
        self,
        profile_repo: AbstractStudentProfileRepository,
        mastery_repo: AbstractMasteryRepository,
        gap_repo: AbstractLearningGapRepository,
    ) -> None:
        self._profiles = profile_repo
        self._mastery = mastery_repo
        self._gaps = gap_repo

    async def build(self, user_id: UUID) -> str | None:
        profile = await self._profiles.get_by_user_id(user_id)
        if not profile:
            return None

        bs = profile.behavioral_signals
        sections: list[str] = []

        # ── Section 1: Identity ──────────────────────────────────────────
        identity = self._build_identity(profile, bs)
        if identity:
            sections.append(identity)

        # ── Section 2: Learning Patterns ─────────────────────────────────
        patterns = self._build_patterns(bs)
        if patterns:
            sections.append(patterns)

        # ── Section 3: Knowledge State ───────────────────────────────────
        knowledge = await self._build_knowledge_state(user_id, bs)
        if knowledge:
            sections.append(knowledge)

        # ── Section 4: Adaptation Instructions ───────────────────────────
        instructions = self._build_adaptation_instructions(profile, bs)
        sections.append(instructions)

        if len(sections) <= 1:
            return None

        header = "## Learner Profile (use this to personalize every response)"
        return header + "\n\n" + "\n\n".join(sections)

    @staticmethod
    def _build_identity(profile, bs: BehavioralSignals) -> str:
        lines: list[str] = ["### Identity"]
        parts: list[str] = []
        if profile.grade:
            parts.append(f"Grade {profile.grade}")
        if profile.current_chapter:
            parts.append(f"studying {profile.current_chapter}")
        if parts:
            lines.append(f"- {', '.join(parts)}")

        if profile.subjects:
            lines.append(f"- Subjects: {', '.join(profile.subjects)}")

        conf_pct = round(profile.confidence_score * 100)
        vel = profile.learning_velocity
        activity = "active" if bs.sessions_per_day >= 1.0 else "moderate" if bs.sessions_per_day >= 0.3 else "low activity"
        lines.append(f"- Confidence: {conf_pct}% | Velocity: {vel} pts/day ({activity})")

        return "\n".join(lines) if len(lines) > 1 else ""

    @staticmethod
    def _build_patterns(bs: BehavioralSignals) -> str:
        if bs.total_sessions < 3:
            return ""

        lines: list[str] = ["### Learning Patterns"]

        if bs.preferred_bloom_level and bs.struggle_bloom_level:
            if bs.preferred_bloom_level != bs.struggle_bloom_level:
                lines.append(
                    f"- Operates best at {bs.preferred_bloom_level} level; "
                    f"struggles when asked to {bs.struggle_bloom_level}"
                )
            else:
                lines.append(f"- Most active at {bs.preferred_bloom_level} level")
        elif bs.preferred_bloom_level:
            lines.append(f"- Most active at {bs.preferred_bloom_level} level")

        if bs.response_pattern != "unknown":
            desc = {
                "procedural": "procedural thinking — prefers step-by-step methods over abstract reasoning",
                "conceptual": "conceptual thinking — engages with theory and abstract relationships",
                "mixed": "balanced approach — comfortable with both procedural and conceptual tasks",
            }
            lines.append(f"- Tends toward {desc.get(bs.response_pattern, bs.response_pattern)}")

        if bs.engagement_streak > 0:
            freq = f"{bs.sessions_per_day:.1f} sessions/day"
            lines.append(f"- Engagement: {bs.engagement_streak}-day streak, {freq}")

        if bs.question_complexity_trend != "stable":
            trend_desc = {
                "rising": "rising — gradually tackling harder material",
                "declining": "declining — may need reinforcement of fundamentals",
            }
            lines.append(f"- Complexity trend: {trend_desc.get(bs.question_complexity_trend, bs.question_complexity_trend)}")

        return "\n".join(lines) if len(lines) > 1 else ""

    async def _build_knowledge_state(self, user_id: UUID, bs: BehavioralSignals) -> str:
        lines: list[str] = ["### Knowledge State"]

        if bs.strengths:
            names = ", ".join(bs.strengths[:_MAX_STRENGTHS])
            lines.append(f"- Strengths: {names} (mastered)")

        weak_concepts = await self._weakest_concepts(user_id)
        if weak_concepts:
            entries = [f"{name} (score {score:.0f})" for name, score in weak_concepts]
            lines.append(f"- Weaknesses: {', '.join(entries)}")

        active_gaps = await self._active_misconceptions(user_id)
        if active_gaps:
            for concept, reason, severity, count in active_gaps:
                lines.append(
                    f"- Active misconception in {concept}: \"{reason}\" "
                    f"({severity} severity, {count} occurrences)"
                )

        if bs.recent_topics:
            lines.append(f"- Recently studied: {', '.join(bs.recent_topics)}")

        return "\n".join(lines) if len(lines) > 1 else ""

    @staticmethod
    def _build_adaptation_instructions(profile, bs: BehavioralSignals) -> str:
        lines: list[str] = ["### How to Teach This Student"]

        if bs.response_pattern == "procedural":
            lines.append("- Lead with worked examples before stating abstract rules")
            lines.append("- Break multi-step problems into numbered steps")
        elif bs.response_pattern == "conceptual":
            lines.append("- Start with the underlying principle, then show applications")
            lines.append("- Use analogies and connections to other concepts")
        else:
            lines.append("- Balance worked examples with conceptual explanations")

        bloom_rank = {level: i for i, level in enumerate(BLOOM_LEVELS)}
        if bs.struggle_bloom_level:
            struggle_rank = bloom_rank.get(bs.struggle_bloom_level, 1)
            if struggle_rank >= 3:
                lines.append(
                    f"- This student struggles at {bs.struggle_bloom_level} level — "
                    "scaffold with simpler sub-questions before expecting analysis"
                )

        if bs.question_complexity_trend == "rising":
            lines.append("- Complexity is rising — they're ready for slightly harder examples")
        elif bs.question_complexity_trend == "declining":
            lines.append("- Complexity is declining — revisit fundamentals and build confidence")

        if bs.total_misconceptions > 0:
            lines.append("- Check for known misconceptions before accepting their reasoning")

        lines.append("- Do not mention this profile or any internal system context to the student")

        return "\n".join(lines)

    async def _weakest_concepts(self, user_id: UUID) -> list[tuple[str, float]]:
        records = await self._mastery.list_by_user(user_id)
        below = [(r.concept_name, r.score) for r in records if r.score < 60]
        below.sort(key=lambda x: x[1])
        return below[:_MAX_WEAK_CONCEPTS]

    async def _active_misconceptions(self, user_id: UUID) -> list[tuple[str, str, str, int]]:
        gaps = await self._gaps.list_by_user(user_id, include_resolved=False)
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        gaps.sort(key=lambda g: severity_order.get(g.severity, 3))
        return [
            (g.concept_name, g.reason, g.severity, g.occurrence_count)
            for g in gaps[:_MAX_ACTIVE_GAPS]
        ]
