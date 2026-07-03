from functools import lru_cache

from src.config import get_settings
from src.infrastructure.imagegen.base import AbstractImageGenerator


@lru_cache
def get_image_generator() -> AbstractImageGenerator:
    settings = get_settings()

    if settings.image_gen_provider == "fal":
        from src.infrastructure.imagegen.fal_provider import FalImageGenerator

        return FalImageGenerator(
            api_key=settings.fal_api_key,
            model=settings.image_gen_model,
        )

    from src.infrastructure.imagegen.stub_provider import StubImageGenerator

    return StubImageGenerator()
