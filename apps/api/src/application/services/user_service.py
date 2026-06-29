from uuid import UUID

import structlog

from src.application.dtos.user import (
    ProfileResponse,
    SettingsResponse,
    UpdateProfileRequest,
    UpdateSettingsRequest,
)
from src.domain.entities.profile import Profile, Settings
from src.domain.exceptions import EntityNotFound
from src.domain.repositories.profile_repository import (
    AbstractProfileRepository,
    AbstractSettingsRepository,
)

logger = structlog.get_logger(__name__)


class UserService:
    def __init__(
        self,
        profile_repo: AbstractProfileRepository,
        settings_repo: AbstractSettingsRepository,
    ) -> None:
        self._profiles = profile_repo
        self._settings = settings_repo

    async def get_profile(self, user_id: UUID) -> ProfileResponse:
        profile = await self._profiles.get_by_user_id(user_id)
        if not profile:
            raise EntityNotFound("Profile not found")
        return self._profile_to_response(profile)

    async def update_profile(self, user_id: UUID, dto: UpdateProfileRequest) -> ProfileResponse:
        profile = await self._profiles.get_by_user_id(user_id)
        if not profile:
            raise EntityNotFound("Profile not found")

        profile.update(
            full_name=dto.full_name,
            bio=dto.bio,
            timezone=dto.timezone,
            language=dto.language,
        )
        updated = await self._profiles.update(profile)
        return self._profile_to_response(updated)

    async def get_settings(self, user_id: UUID) -> SettingsResponse:
        settings = await self._settings.get_by_user_id(user_id)
        if not settings:
            raise EntityNotFound("Settings not found")
        return self._settings_to_response(settings)

    async def update_settings(self, user_id: UUID, dto: UpdateSettingsRequest) -> SettingsResponse:
        settings = await self._settings.get_by_user_id(user_id)
        if not settings:
            raise EntityNotFound("Settings not found")

        if dto.theme is not None:
            settings.theme = dto.theme
        if dto.notifications_enabled is not None:
            settings.notifications_enabled = dto.notifications_enabled
        if dto.llm_model is not None:
            settings.llm_model = dto.llm_model
        if dto.temperature is not None:
            settings.temperature = dto.temperature

        updated = await self._settings.update(settings)
        return self._settings_to_response(updated)

    @staticmethod
    def _profile_to_response(p: Profile) -> ProfileResponse:
        return ProfileResponse(
            id=str(p.id),
            user_id=str(p.user_id),
            full_name=p.full_name,
            avatar_url=p.avatar_url,
            bio=p.bio,
            timezone=p.timezone,
            language=p.language,
            created_at=p.created_at.isoformat(),
            updated_at=p.updated_at.isoformat(),
        )

    @staticmethod
    def _settings_to_response(s: Settings) -> SettingsResponse:
        return SettingsResponse(
            id=str(s.id),
            user_id=str(s.user_id),
            theme=s.theme,
            notifications_enabled=s.notifications_enabled,
            llm_model=s.llm_model,
            temperature=s.temperature,
            created_at=s.created_at.isoformat(),
            updated_at=s.updated_at.isoformat(),
        )
