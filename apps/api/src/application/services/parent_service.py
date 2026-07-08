"""
ParentService — Parent Persona (ADR-013).

Consent-based guardian links: a student issues a short-lived code (Redis TTL),
a parent redeems it to create a durable link, and parents then get read-only
views of their child's learning composed from existing analytics services.
"""
import secrets
from uuid import UUID

import redis.asyncio as aioredis
import structlog

from src.domain.entities.guardian import GuardianLink
from src.domain.entities.school import Role
from src.domain.exceptions import (
    AuthorizationError,
    EntityNotFound,
    ValidationError,
)
from src.domain.repositories.guardian_repository import AbstractGuardianRepository
from src.domain.repositories.learning_repository import (
    AbstractLearningGapRepository,
    AbstractLearningSessionRepository,
    AbstractMasteryRepository,
    AbstractStudentProfileRepository,
)
from src.domain.repositories.user_repository import AbstractUserRepository

logger = structlog.get_logger(__name__)

_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
_CODE_PREFIX = "parent-code:"


class ParentService:
    def __init__(
        self,
        guardian_repo: AbstractGuardianRepository,
        user_repo: AbstractUserRepository,
        profile_repo: AbstractStudentProfileRepository,
        mastery_repo: AbstractMasteryRepository,
        gap_repo: AbstractLearningGapRepository,
        session_repo: AbstractLearningSessionRepository,
        redis: aioredis.Redis | None = None,
        code_ttl: int = 604800,
    ) -> None:
        self._guardians = guardian_repo
        self._users = user_repo
        self._profiles = profile_repo
        self._mastery = mastery_repo
        self._gaps = gap_repo
        self._sessions = session_repo
        self._redis = redis
        self._code_ttl = code_ttl

    # ── Student side: issue / list / revoke ──────────────────────────────────

    async def generate_link_code(self, student_id: UUID) -> tuple[str, int]:
        if not self._redis:
            raise ValidationError("Parent linking is temporarily unavailable")
        code = "".join(secrets.choice(_CODE_ALPHABET) for _ in range(8))
        try:
            await self._redis.set(
                f"{_CODE_PREFIX}{code}", str(student_id), ex=self._code_ttl
            )
        except Exception as exc:
            logger.warning("parent_code_issue_failed", error=str(exc))
            raise ValidationError("Parent linking is temporarily unavailable") from exc
        return code, self._code_ttl

    async def list_guardians(
        self, student_id: UUID
    ) -> list[tuple[GuardianLink, str, str]]:
        links = await self._guardians.list_by_student(student_id)
        out: list[tuple[GuardianLink, str, str]] = []
        for link in links:
            parent = await self._users.get_by_id(link.parent_id)
            if parent:
                out.append((link, parent.username, parent.email))
        return out

    async def revoke_guardian(self, student_id: UUID, parent_id: UUID) -> None:
        link = await self._guardians.get(parent_id, student_id)
        if not link:
            raise EntityNotFound("Guardian link not found")
        link.status = "revoked"
        await self._guardians.update(link)

    # ── Parent side: link / list children / overview ─────────────────────────

    async def link_by_code(self, parent_id: UUID, code: str) -> tuple[UUID, str]:
        if not self._redis:
            raise ValidationError("Parent linking is temporarily unavailable")
        try:
            raw = await self._redis.get(f"{_CODE_PREFIX}{code.strip().upper()}")
        except Exception as exc:
            raise ValidationError("Parent linking is temporarily unavailable") from exc
        if not raw:
            raise EntityNotFound("Invalid or expired link code")

        student_id = UUID(raw)
        if student_id == parent_id:
            raise ValidationError("You cannot link to your own account")

        existing = await self._guardians.get(parent_id, student_id)
        if existing and existing.status == "active":
            student = await self._users.get_by_id(student_id)
            return student_id, (student.username if student else "")
        if existing:
            existing.status = "active"
            await self._guardians.update(existing)
        else:
            await self._guardians.create(
                GuardianLink(parent_id=parent_id, student_id=student_id)
            )
        await self._promote_parent(parent_id)
        student = await self._users.get_by_id(student_id)
        logger.info("parent_linked", parent_id=str(parent_id), student_id=str(student_id))
        return student_id, (student.username if student else "")

    async def list_children(
        self, parent_id: UUID
    ) -> list[tuple[GuardianLink, str, str, str | None]]:
        links = await self._guardians.list_by_parent(parent_id)
        out: list[tuple[GuardianLink, str, str, str | None]] = []
        for link in links:
            student = await self._users.get_by_id(link.student_id)
            if not student:
                continue
            profile = await self._profiles.get_by_user_id(link.student_id)
            grade = profile.grade if profile else None
            out.append((link, student.username, student.email, grade))
        return out

    async def assert_linked(self, parent_id: UUID, student_id: UUID) -> None:
        link = await self._guardians.get(parent_id, student_id)
        if not link or link.status != "active":
            raise AuthorizationError("You are not linked to this student")

    async def child_overview(self, parent_id: UUID, student_id: UUID) -> dict:
        await self.assert_linked(parent_id, student_id)

        student = await self._users.get_by_id(student_id)
        if not student:
            raise EntityNotFound("Student not found")

        # Fetch each source once, then derive aggregates locally — avoids the
        # duplicate mastery/gap/session queries a LearningAnalyticsService call
        # would repeat under the hood.
        profile = await self._profiles.get_by_user_id(student_id)
        mastery = await self._mastery.list_by_user(student_id)
        gaps = await self._gaps.list_by_user(student_id, include_resolved=False)
        recent = await self._sessions.list_by_user(student_id, limit=8, offset=0)
        total_sessions = await self._sessions.count_by_user(student_id)

        average_mastery = (
            round(sum(r.score for r in mastery) / len(mastery), 2) if mastery else 0.0
        )
        mastered_count = sum(1 for r in mastery if r.label == "mastered")

        strengths = [
            r.concept_name
            for r in sorted(mastery, key=lambda r: r.score, reverse=True)
            if r.score >= 70
        ][:5]
        weak_areas = [
            {"concept": g.concept_name, "severity": g.severity} for g in gaps[:5]
        ]
        recent_activity = [
            {
                "question": s.question,
                "subject": s.subject,
                "created_at": s.created_at.isoformat(),
            }
            for s in recent
        ]
        streak = 0
        if profile and isinstance(profile.behavioral_signals, dict):
            streak = int(profile.behavioral_signals.get("engagement_streak", 0) or 0)

        return {
            "student_id": str(student_id),
            "username": student.username,
            "grade": profile.grade if profile else None,
            "average_mastery": average_mastery,
            "mastered_count": mastered_count,
            "total_concepts": len(mastery),
            "active_gaps": len(gaps),
            "total_sessions": total_sessions,
            "engagement_streak": streak,
            "strengths": strengths,
            "weak_areas": weak_areas,
            "recent_activity": recent_activity,
        }

    # ── Internal ─────────────────────────────────────────────────────────────

    async def _promote_parent(self, parent_id: UUID) -> None:
        user = await self._users.get_by_id(parent_id)
        if not user or user.is_admin:
            return
        if user.role in (Role.STUDENT,) or not user.role:
            user.role = Role.PARENT
            await self._users.update(user)
