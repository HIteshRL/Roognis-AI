from functools import lru_cache

from src.config import get_settings
from src.infrastructure.vision.base import AbstractVisionProvider


@lru_cache
def get_vision_provider() -> AbstractVisionProvider:
    settings = get_settings()

    # Only Groq is wired today; the Literal on Settings.vision_provider keeps
    # this exhaustive. New backends slot in here without touching callers.
    from src.infrastructure.vision.groq_vision_provider import GroqVisionProvider

    return GroqVisionProvider(
        api_key=settings.groq_api_key,
        model=settings.vision_model,
        temperature=settings.ocr_temperature,
        max_tokens=settings.groq_max_tokens,
    )
