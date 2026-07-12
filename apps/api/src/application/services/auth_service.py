import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

import structlog
from jose import JWTError, jwt
from passlib.context import CryptContext

from src.application.dtos.auth import LoginRequest, RegisterRequest, TokenPayload
from src.application.dtos.user import UserResponse
from src.config import Settings
from src.domain.entities.lms import AuthToken
from src.domain.entities.profile import Profile
from src.domain.entities.profile import Settings as UserSettings
from src.domain.entities.user import User
from src.domain.exceptions import AuthenticationError, DuplicateEntity, EntityNotFound
from src.domain.repositories.lms_repository import (
    AbstractAuthTokenRepository,
    AbstractSessionRepository,
)
from src.domain.repositories.profile_repository import (
    AbstractProfileRepository,
    AbstractSettingsRepository,
)
from src.domain.repositories.user_repository import AbstractUserRepository
from src.infrastructure.email.base import AbstractEmailProvider

logger = structlog.get_logger(__name__)

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
_ALGORITHM = "HS256"
_TOKEN_EXPIRE_HOURS = 24 * 7  # 7 days
_REFRESH_EXPIRE_DAYS = 30
_RESET_TOKEN_TTL_MINUTES = 30
_VERIFY_TOKEN_TTL_HOURS = 48


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


class AuthService:
    def __init__(
        self,
        user_repo: AbstractUserRepository,
        profile_repo: AbstractProfileRepository,
        settings_repo: AbstractSettingsRepository,
        app_settings: Settings,
        auth_token_repo: AbstractAuthTokenRepository | None = None,
        session_repo: AbstractSessionRepository | None = None,
        email_provider: AbstractEmailProvider | None = None,
    ) -> None:
        self._users = user_repo
        self._profiles = profile_repo
        self._settings = settings_repo
        self._secret = app_settings.api_secret_key
        self._auth_tokens = auth_token_repo
        self._sessions = session_repo
        self._email = email_provider
        self._frontend_url = app_settings.frontend_base_url

    async def register(self, dto: RegisterRequest) -> tuple[UserResponse, str]:
        if await self._users.get_by_email(dto.email):
            raise DuplicateEntity("Email already registered")
        if await self._users.get_by_username(dto.username):
            raise DuplicateEntity("Username already taken")

        user = User(
            email=dto.email,
            username=dto.username,
            password_hash=_pwd_context.hash(dto.password),
            role=dto.role,
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

    # ── Refresh tokens ────────────────────────────────────────────────────────

    async def issue_refresh_token(
        self, user_id: UUID, ip_address: str | None = None, user_agent: str | None = None
    ) -> str:
        if not self._sessions:
            raise AuthenticationError("Refresh tokens are not enabled")
        raw = secrets.token_urlsafe(48)
        await self._sessions.create(
            user_id=user_id,
            token_hash=_hash_token(raw),
            expires_at=datetime.now(UTC) + timedelta(days=_REFRESH_EXPIRE_DAYS),
            ip_address=ip_address,
            user_agent=user_agent,
        )
        return raw

    async def refresh_access_token(self, refresh_token: str) -> tuple[UserResponse, str, str]:
        """Rotate: validate the refresh token, issue a new access + refresh pair."""
        if not self._sessions:
            raise AuthenticationError("Refresh tokens are not enabled")
        token_hash = _hash_token(refresh_token)
        user_id = await self._sessions.get_user_id_by_hash(token_hash)
        if not user_id:
            raise AuthenticationError("Invalid or expired refresh token")
        user = await self._users.get_by_id(user_id)
        if not user or not user.is_active:
            raise AuthenticationError("User not found or inactive")
        await self._sessions.delete_by_hash(token_hash)
        new_refresh = await self.issue_refresh_token(user.id)
        return self._to_response(user), self._create_token(user), new_refresh

    async def revoke_refresh_token(self, refresh_token: str) -> None:
        if self._sessions:
            await self._sessions.delete_by_hash(_hash_token(refresh_token))

    # ── Password reset ────────────────────────────────────────────────────────

    async def request_password_reset(self, email: str) -> None:
        """Always succeeds from the caller's view — never reveals whether the
        email exists (user-enumeration hardening)."""
        if not self._auth_tokens:
            return
        user = await self._users.get_by_email(email)
        if not user or not user.is_active:
            logger.info("password_reset_requested_unknown_email")
            return
        await self._auth_tokens.invalidate_for_user(user.id, "password_reset")
        raw = secrets.token_urlsafe(32)
        await self._auth_tokens.create(
            AuthToken(
                user_id=user.id,
                token_hash=_hash_token(raw),
                purpose="password_reset",
                expires_at=datetime.now(UTC) + timedelta(minutes=_RESET_TOKEN_TTL_MINUTES),
            )
        )
        if self._email:
            await self._email.send(
                to=user.email,
                subject="Reset your Roognis password",
                body=(
                    f"Use this link to reset your password (valid "
                    f"{_RESET_TOKEN_TTL_MINUTES} minutes):\n"
                    f"{self._frontend_url}/reset-password?token={raw}"
                ),
            )
        logger.info("password_reset_requested", user_id=str(user.id))

    async def confirm_password_reset(self, token: str, new_password: str) -> None:
        record = await self._consume_token(token, "password_reset")
        user = await self._users.get_by_id(record.user_id)
        if not user:
            raise EntityNotFound("User not found")
        user.password_hash = _pwd_context.hash(new_password)
        await self._users.update(user)
        if self._sessions:
            await self._sessions.delete_for_user(user.id)  # log out everywhere
        logger.info("password_reset_completed", user_id=str(user.id))

    async def change_password(
        self, user_id: UUID, current_password: str, new_password: str
    ) -> None:
        user = await self._users.get_by_id(user_id)
        if not user or not _pwd_context.verify(current_password, user.password_hash):
            raise AuthenticationError("Current password is incorrect")
        user.password_hash = _pwd_context.hash(new_password)
        await self._users.update(user)
        logger.info("password_changed", user_id=str(user_id))

    # ── Email verification ────────────────────────────────────────────────────

    async def request_email_verification(self, user_id: UUID) -> None:
        if not self._auth_tokens:
            return
        user = await self._users.get_by_id(user_id)
        if not user or user.is_verified:
            return
        await self._auth_tokens.invalidate_for_user(user.id, "email_verify")
        raw = secrets.token_urlsafe(32)
        await self._auth_tokens.create(
            AuthToken(
                user_id=user.id,
                token_hash=_hash_token(raw),
                purpose="email_verify",
                expires_at=datetime.now(UTC) + timedelta(hours=_VERIFY_TOKEN_TTL_HOURS),
            )
        )
        if self._email:
            await self._email.send(
                to=user.email,
                subject="Verify your Roognis email",
                body=(
                    f"Confirm your email address:\n"
                    f"{self._frontend_url}/verify-email?token={raw}"
                ),
            )
        logger.info("email_verification_requested", user_id=str(user.id))

    async def confirm_email_verification(self, token: str) -> UserResponse:
        record = await self._consume_token(token, "email_verify")
        user = await self._users.get_by_id(record.user_id)
        if not user:
            raise EntityNotFound("User not found")
        user.is_verified = True
        updated = await self._users.update(user)
        logger.info("email_verified", user_id=str(user.id))
        return self._to_response(updated)

    async def _consume_token(self, raw: str, purpose: str) -> AuthToken:
        if not self._auth_tokens:
            raise AuthenticationError("Token flows are not enabled")
        record = await self._auth_tokens.get_by_hash(_hash_token(raw))
        if not record or record.purpose != purpose or not record.is_valid_at(datetime.now(UTC)):
            raise AuthenticationError("Invalid or expired token")
        await self._auth_tokens.mark_used(record.id)
        return record

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
