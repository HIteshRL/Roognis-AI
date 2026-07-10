from functools import lru_cache

from src.config import get_settings
from src.infrastructure.llm.base import AbstractLLMProvider
from src.infrastructure.llm.groq_provider import GroqProvider


@lru_cache
def get_llm_provider() -> AbstractLLMProvider:
    """
    Returns the configured LLM provider.
    Swap the provider here without touching any application service.
    """
    settings = get_settings()
    return GroqProvider(api_key=settings.groq_api_key)
