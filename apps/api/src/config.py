from functools import lru_cache
from typing import Literal

from pydantic import Field, PostgresDsn, RedisDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ──────────────────────────────────────────────────────────
    app_env: Literal["development", "staging", "production"] = "development"
    app_version: str = "0.1.0"
    app_name: str = "Roognis AI API"

    # ── Server ───────────────────────────────────────────────────────────────
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_secret_key: str = Field(..., min_length=32)

    # ── Database ─────────────────────────────────────────────────────────────
    database_url: PostgresDsn

    # ── Redis ────────────────────────────────────────────────────────────────
    redis_url: RedisDsn

    # ── CORS ─────────────────────────────────────────────────────────────────
    cors_origins: list[str] = ["http://localhost:3000"]
    cors_allow_credentials: bool = True

    # ── Clerk ────────────────────────────────────────────────────────────────
    clerk_secret_key: str = ""
    clerk_publishable_key: str = ""

    # ── LLM ──────────────────────────────────────────────────────────────────
    groq_api_key: str
    groq_default_model: str = "llama-3.3-70b-versatile"
    groq_max_tokens: int = 4096
    groq_temperature: float = 0.7

    # ── Rate Limiting ────────────────────────────────────────────────────────
    rate_limit_default: int = 100
    rate_limit_chat: int = 20
    rate_limit_auth: int = 10
    rate_limit_window_seconds: int = 60

    # ── Logging ───────────────────────────────────────────────────────────────
    log_level: str = "INFO"
    log_format: Literal["json", "console"] = "json"

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def database_url_str(self) -> str:
        return str(self.database_url)


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
