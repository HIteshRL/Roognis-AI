from uuid import UUID

import structlog

from src.domain.entities.learning import BehavioralSignals, StudentProfile
from src.domain.repositories.learning_repository import AbstractStudentProfileRepository

logger = structlog.get_logger(__name__)


class StudentProfileService:
    def __init__(self, repo: AbstractStudentProfileRepository) -> None:
        self._repo = repo

    async def get_or_create(self, user_id: UUID) -> StudentProfile:
        profile = await self._repo.get_by_user_id(user_id)
        if profile:
            return profile
        profile = StudentProfile(user_id=user_id)
        profile = await self._repo.create(profile)
        logger.info("student_profile_created", user_id=str(user_id))
        return profile

    async def get(self, user_id: UUID) -> StudentProfile | None:
        return await self._repo.get_by_user_id(user_id)

    async def update(
        self,
        user_id: UUID,
        institution: str | None = None,
        grade: str | None = None,
        subjects: list[str] | None = None,
        current_chapter: str | None = None,
    ) -> StudentProfile:
        profile = await self.get_or_create(user_id)
        if institution is not None:
            profile.institution = institution
        if grade is not None:
            profile.grade = grade
        if subjects is not None:
            profile.subjects = subjects
        if current_chapter is not None:
            profile.current_chapter = current_chapter
        profile.touch()
        return await self._repo.update(profile)

    async def touch(self, user_id: UUID) -> None:
        profile = await self._repo.get_by_user_id(user_id)
        if profile:
            profile.touch()
            await self._repo.update(profile)

    async def refresh_confidence(self, user_id: UUID, avg_mastery: float) -> None:
        profile = await self._repo.get_by_user_id(user_id)
        if profile:
            profile.update_confidence(avg_mastery)
            await self._repo.update(profile)

    async def update_velocity(self, user_id: UUID, velocity: float) -> None:
        profile = await self._repo.get_by_user_id(user_id)
        if profile:
            profile.learning_velocity = velocity
            await self._repo.update(profile)

    async def update_behavioral_signals(self, user_id: UUID, signals: BehavioralSignals) -> None:
        profile = await self._repo.get_by_user_id(user_id)
        if profile:
            profile.behavioral_signals = signals
            await self._repo.update(profile)
