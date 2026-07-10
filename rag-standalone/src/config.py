"""
Standalone settings for the RAG component.

This is a slimmed replacement for the app's full `Settings` — it exposes ONLY
the fields the RAG factories read, and requires no database / auth / web config.
All values come from environment variables (or a .env file) with sane defaults.
"""
from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    # ── LLM (Groq) ───────────────────────────────────────────────────────────
    groq_api_key: str = ""
    groq_default_model: str = "llama-3.3-70b-versatile"
    groq_max_tokens: int = 4096

    # ── Embeddings ───────────────────────────────────────────────────────────
    embedding_provider: Literal["fastembed", "openai"] = "fastembed"
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    openai_api_key: str = ""
    openai_embedding_model: str = "text-embedding-3-small"

    # ── Vector store (Qdrant) ────────────────────────────────────────────────
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str = ""
    qdrant_collection: str = "rag_standalone"

    # ── Chunking / Retrieval ─────────────────────────────────────────────────
    chunk_size: int = 512
    chunk_overlap: int = 64
    chunk_strategy: Literal["fixed", "semantic", "sliding"] = "fixed"
    retrieval_top_k: int = 5
    retrieval_score_threshold: float = 0.35

    # ── Vision OCR ───────────────────────────────────────────────────────────
    ocr_enabled: bool = True
    vision_model: str = "meta-llama/llama-4-scout-17b-16e-instruct"
    ocr_min_chars_per_page: int = 20
    ocr_max_pages: int = 40
    ocr_max_image_dimension: int = 1536
    ocr_image_format: Literal["jpeg", "png"] = "jpeg"
    ocr_temperature: float = 0.0

    # Present so the vision factory's field read never misses.
    vision_provider: Literal["groq"] = "groq"
    vector_provider: Literal["qdrant"] = "qdrant"


@lru_cache
def get_settings() -> Settings:
    return Settings()
