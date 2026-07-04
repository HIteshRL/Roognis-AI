from datetime import UTC, datetime, timedelta
from uuid import UUID

import structlog
from jose import JWTError, jwt
from passlib.context import CryptContext

from src.application.dtos.auth import LoginRequest, RegisterRequest, TokenPayload
from src.application.dtos.user import UserResponse
from src.config import Settings
from src.domain.entities.profile import Profile
from src.domain.entities.profile import Settings as UserSettings
from src.domain.entities.user import User
from src.domain.exceptions import AuthenticationError, DuplicateEntity
from src.domain.repositories.profile_repository import (
    AbstractProfileRepository,
    AbstractSettingsRepository,
)
from src.domain.repositories.user_repository import AbstractUserRepository

logger = structlog.get_logger(__name__)

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
_ALGORITHM = "HS256"
_TOKEN_EXPIRE_HOURS = 24 * 7  # 7 days


class AuthService:
    def __init__(
        self,
        user_repo: AbstractUserRepository,
        profile_repo: AbstractProfileRepository,
        settings_repo: AbstractSettingsRepository,
        app_settings: Settings,
    ) -> None:
        self._users = user_repo
        self._profiles = profile_repo
        self._settings = settings_repo
        self._secret = app_settings.api_secret_key

    async def register(self, dto: RegisterRequest) -> tuple[UserResponse, str]:
        if await self._users.get_by_email(dto.email):
            raise DuplicateEntity("Email already registered")
        if await self._users.get_by_username(dto.username):
            raise DuplicateEntity("Username already taken")

        user = User(
            email=dto.email,
            username=dto.username,
            password_hash=_pwd_context.hash(dto.password),
        )
        user = await self._users.create(user)

        # Create default profile and settings
        await self._profiles.create(Profile(user_id=user.id))
        await self._settings.create(UserSettings(user_id=user.id))

        token = self._create_token(user)
        logger.info("user_registered", user_id=str(user.id), email=user.email)
        return self._to_response(user), token

    async def login(self, dto: LoginRequest) -> tuple[UserResponse, str]:
        user = await self._users.get_by_email(dto.email)
        if not user or not _pwd_context.verify(dto.password, user.password_hash):
            raise AuthenticationError("Invalid email or password")
        if not user.is_active:
            raise AuthenticationError("Account is deactivated")

        token = self._create_token(user)
        logger.info("user_logged_in", user_id=str(user.id))
        return self._to_response(user), token

    async def get_current_user(self, token: str) -> UserResponse:
        payload = self._decode_token(token)
        user = await self._users.get_by_id(UUID(payload.sub))
        if not user or not user.is_active:
            raise AuthenticationError("User not found or inactive")
        return self._to_response(user)

    async def sync_clerk_user(self, clerk_id: str, email: str, username: str | None) -> UserResponse:
        existing = await self._users.get_by_clerk_id(clerk_id)
        if existing:
            return self._to_response(existing)

        by_email = await self._users.get_by_email(email)
        if by_email:
            by_email.link_clerk(clerk_id)
            updated = await self._users.update(by_email)
            return self._to_response(updated)

        uname = username or email.split("@")[0]
        base, suffix = uname, 0
        while await self._users.get_by_username(uname):
            suffix += 1
            uname = f"{base}{suffix}"

        user = User(
            email=email,
            username=uname,
            password_hash="",  # Clerk-managed auth — no local password
            clerk_id=clerk_id,
            is_verified=True,
        )
        user = await self._users.create(user)
        await self._profiles.create(Profile(user_id=user.id))
        await self._settings.create(UserSettings(user_id=user.id))
        return self._to_response(user)

    def _create_token(self, user: User) -> str:
        expire = datetime.now(UTC) + timedelta(hours=_TOKEN_EXPIRE_HOURS)
        return jwt.encode(
            {"sub": str(user.id), "email": user.email, "exp": expire},
            self._secret,
            algorithm=_ALGORITHM,
        )

    def _decode_token(self, token: str) -> TokenPayload:
        try:
            payload = jwt.decode(token, self._secret, algorithms=[_ALGORITHM])
            return TokenPayload(**payload)
        except JWTError as e:
            raise AuthenticationError("Invalid or expired token") from e

    @staticmethod
    def _to_response(user: User) -> UserResponse:
        return UserResponse(
            id=str(user.id),
            email=user.email,
            username=user.username,
            is_active=user.is_active,
            is_verified=user.is_verified,
            is_admin=user.is_admin,
            role=user.role,
            created_at=user.created_at.isoformat(),
            updated_at=user.updated_at.isoformat(),
        )
