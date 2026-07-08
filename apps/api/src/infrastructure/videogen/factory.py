from functools import lru_cache

from src.config import get_settings
from src.infrastructure.videogen.base import AbstractVideoGenerator


@lru_cache
def get_video_generator() -> AbstractVideoGenerator:
    settings = get_settings()

    if settings.video_gen_provider == "fal":
        from src.infrastructure.videogen.fal_provider import FalVideoGenerator

        return FalVideoGenerator(
            api_key=settings.fal_api_key,
            model=settings.fal_video_model,
        )

    if settings.video_gen_provider == "ltx":
        from src.infrastructure.videogen.ltx_provider import LTXVideoGenerator

        return LTXVideoGenerator(
            model_id=settings.ltx_model_id,
            guidance_scale=settings.video_guidance_scale,
        )

    from src.infrastructure.videogen.stub_provider import StubVideoGenerator

    return StubVideoGenerator()
