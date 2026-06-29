from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.user import User
from src.domain.repositories.user_repository import AbstractUserRepository
from src.infrastructure.database.models.user import UserModel


def _to_entity(m: UserModel) -> User:
    u = User.__new__(User)
    u.id = UUID(m.id)
    u.email = m.email
    u.username = m.username
    u.password_hash = m.password_hash
    u.is_active = m.is_active
    u.is_verified = m.is_verified
    u.clerk_id = m.clerk_id
    u.created_at = m.created_at
    u.updated_at = m.updated_at
    return u


class UserRepository(AbstractUserRepository):
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(self, user: User) -> User:
        model = UserModel(
            id=str(user.id),
            email=user.email,
            username=user.username,
            password_hash=user.password_hash,
            is_active=user.is_active,
            is_verified=user.is_verified,
            clerk_id=user.clerk_id,
        )
        self._db.add(model)
        await self._db.flush()
        await self._db.refresh(model)
        return _to_entity(model)

    async def get_by_id(self, user_id: UUID) -> User | None:
        result = await self._db.execute(
            select(UserModel).where(UserModel.id == str(user_id))
        )
        model = result.scalar_one_or_none()
        return _to_entity(model) if model else None

    async def get_by_email(self, email: str) -> User | None:
        result = await self._db.execute(select(UserModel).where(UserModel.email == email))
        model = result.scalar_one_or_none()
        return _to_entity(model) if model else None

    async def get_by_username(self, username: str) -> User | None:
        result = await self._db.execute(
            select(UserModel).where(UserModel.username == username)
        )
        model = result.scalar_one_or_none()
        return _to_entity(model) if model else None

    async def get_by_clerk_id(self, clerk_id: str) -> User | None:
        result = await self._db.execute(
            select(UserModel).where(UserModel.clerk_id == clerk_id)
        )
        model = result.scalar_one_or_none()
        return _to_entity(model) if model else None

    async def update(self, user: User) -> User:
        result = await self._db.execute(
            select(UserModel).where(UserModel.id == str(user.id))
        )
        model = result.scalar_one()
        model.email = user.email
        model.username = user.username
        model.password_hash = user.password_hash
        model.is_active = user.is_active
        model.is_verified = user.is_verified
        model.clerk_id = user.clerk_id
        await self._db.flush()
        await self._db.refresh(model)
        return _to_entity(model)

    async def delete(self, user_id: UUID) -> None:
        result = await self._db.execute(
            select(UserModel).where(UserModel.id == str(user_id))
        )
        model = result.scalar_one_or_none()
        if model:
            await self._db.delete(model)
            await self._db.flush()
