import base64

from src.infrastructure.imagegen.base import AbstractImageGenerator, ImageResult

# Minimal valid 1x1 PNG — lets the full pipeline run with no Fal key / no network.
_STUB_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
)


class StubImageGenerator(AbstractImageGenerator):
    """Offline stand-in for local dev / tests — returns a tiny placeholder PNG."""

    @property
    def provider_name(self) -> str:
        return "stub"

    async def generate(self, prompt: str, size: str = "1024x1024") -> ImageResult:
        return ImageResult(data=_STUB_PNG, content_type="image/png")
