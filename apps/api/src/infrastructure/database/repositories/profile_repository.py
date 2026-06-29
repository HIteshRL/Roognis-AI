from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.profile import Profile, Settings
from src.domain.repositories.profile_repository import (
    AbstractProfileRepository,
    AbstractSettingsRepository,
)
from src.infrastructure.database.models.profile import ProfileModel, SettingsModel


def _to_profile(m: ProfileModel) -> Profile:
    p = Profile.__new__(Profile)
    p.id = UUID(m.id)
    p.user_id = UUID(m.user_id)
    p.full_name = m.full_name
    p.avatar_url = m.avatar_url
    p.bio = m.bio
    p.timezone = m.timezone
    p.language = m.language
    p.created_at = m.created_at
    p.updated_at = m.updated_at
    return p


def _to_settings(m: SettingsModel) -> Settings:
    s = Settings.__new__(Settings)
    s.id = UUID(m.id)
    s.user_id = UUID(m.user_id)
    s.theme = m.theme
    s.notifications_enabled = m.notifications_enabled
    s.llm_model = m.llm_model
    s.temperature = m.temperature
    s.created_at = m.created_at
    s.updated_at = m.updated_at
    return s


class ProfileRepository(AbstractProfileRepository):
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(self, profile: Profile) -> Profile:
        model = ProfileModel(
            id=str(profile.id),
            user_id=str(profile.user_id),
            full_name=profile.full_name,
            avatar_url=profile.avatar_url,
            bio=profile.bio,
            timezone=profile.timezone,
            language=profile.language,
        )
        self._db.add(model)
        await self._db.flush()
        await self._db.refresh(model)
        return _to_profile(model)

    async def get_by_user_id(self, user_id: UUID) -> Profile | None:
        result = await self._db.execute(
            select(ProfileModel).where(ProfileModel.user_id == str(user_id))
        )
        model = result.scalar_one_or_none()
        return _to_profile(model) if model else None

    async def update(self, profile: Profile) -> Profile:
        result = await self._db.execute(
            select(ProfileModel).where(ProfileModel.id == str(profile.id))
        )
        model = result.scalar_one()
        model.full_name = profile.full_name
        model.avatar_url = profile.avatar_url
        model.bio = profile.bio
        model.timezone = profile.timezone
        model.language = profile.language
        await self._db.flush()
        await self._db.refresh(model)
        return _to_profile(model)


class SettingsRepository(AbstractSettingsRepository):
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(self, settings: Settings) -> Settings:
        model = SettingsModel(
            id=str(settings.id),
            user_id=str(settings.user_id),
            theme=settings.theme,
            notifications_enabled=settings.notifications_enabled,
            llm_model=settings.llm_model,
            temperature=settings.temperature,
        )
        self._db.add(model)
        await self._db.flush()
        await self._db.refresh(model)
        return _to_settings(model)

    async def get_by_user_id(self, user_id: UUID) -> Settings | None:
        result = await self._db.execute(
            select(SettingsModel).where(SettingsModel.user_id == str(user_id))
        )
        model = result.scalar_one_or_none()
        return _to_settings(model) if model else None

    async def update(self, settings: Settings) -> Settings:
        result = await self._db.execute(
            select(SettingsModel).where(SettingsModel.id == str(settings.id))
        )
        model = result.scalar_one()
        model.theme = settings.theme
        model.notifications_enabled = settings.notifications_enabled
        model.llm_model = settings.llm_model
        model.temperature = settings.temperature
        await self._db.flush()
        await self._db.refresh(model)
        return _to_settings(model)
