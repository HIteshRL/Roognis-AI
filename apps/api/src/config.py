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
    app_version: str = "0.2.0"
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

    # ── Learner Intelligence bridge (default OFF) ────────────────────────────
    # Shared secret for the demo→engine evidence-ingest endpoint. When empty the
    # endpoint is disabled entirely. Set BRIDGE_INGEST_TOKEN to enable bridging.
    bridge_ingest_token: str = ""

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

    # ── Logging ──────────────────────────────────────────────────────────────
    log_level: str = "INFO"
    log_format: Literal["json", "console"] = "json"

    # ── Phase 0.2: Vector Database ───────────────────────────────────────────
    vector_provider: Literal["qdrant"] = "qdrant"
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str = ""
    qdrant_collection: str = "roognis_knowledge"

    # ── Phase 0.2: Embeddings ────────────────────────────────────────────────
    embedding_provider: Literal["fastembed", "openai"] = "fastembed"
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_dimension: int = 384
    openai_api_key: str = ""
    openai_embedding_model: str = "text-embedding-3-small"

    # ── Phase 0.2: Chunking ──────────────────────────────────────────────────
    chunk_size: int = 512
    chunk_overlap: int = 64
    chunk_strategy: Literal["fixed", "semantic", "sliding"] = "fixed"

    # ── Phase 0.2: Retrieval ─────────────────────────────────────────────────
    retrieval_top_k: int = 5
    retrieval_score_threshold: float = 0.35
    retrieval_enabled: bool = True

    # ── Phase 0.2: Storage ───────────────────────────────────────────────────
    storage_provider: Literal["local"] = "local"
    storage_local_path: str = "./uploads"
    max_upload_size_mb: int = 50

    # ── Phase 0.6: Vision / OCR ──────────────────────────────────────────────
    # Scanned PDFs and uploaded images have no text layer. When enabled, pages
    # with little or no extractable text are sent to a Groq vision model that
    # transcribes them so the content becomes RAG-searchable. Fail-open: any
    # OCR error leaves the original (possibly empty) page text untouched.
    ocr_enabled: bool = True
    vision_provider: Literal["groq"] = "groq"
    vision_model: str = "meta-llama/llama-4-scout-17b-16e-instruct"
    ocr_min_chars_per_page: int = 20
    ocr_max_pages: int = 40
    ocr_max_image_dimension: int = 1536
    ocr_image_format: Literal["jpeg", "png"] = "jpeg"
    ocr_temperature: float = 0.0

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def database_url_str(self) -> str:
        return str(self.database_url)

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
