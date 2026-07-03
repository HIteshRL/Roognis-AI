import httpx
import structlog

from src.infrastructure.imagegen.base import AbstractImageGenerator, ImageResult

logger = structlog.get_logger(__name__)

_FAL_SYNC_BASE = "https://fal.run"
_TIMEOUT_SECONDS = 60.0


def _parse_size(size: str) -> tuple[int, int]:
    try:
        w, h = size.lower().split("x")
        return int(w), int(h)
    except (ValueError, AttributeError):
        return 1024, 1024


class FalImageGenerator(AbstractImageGenerator):
    """Text-to-image via Fal's synchronous inference endpoint.

    Uses the hosted `fal-ai/flux/schnell` (or configured) model. Fast enough
    (~1-3s) to run inline on each answer. Raises on failure so the caller can
    fail-open and skip the image.
    """

    def __init__(self, api_key: str, model: str = "fal-ai/flux/schnell") -> None:
        self._api_key = api_key
        self._model = model

    @property
    def provider_name(self) -> str:
        return "fal"

    async def generate(self, prompt: str, size: str = "1024x1024") -> ImageResult:
        if not self._api_key:
            raise RuntimeError("FAL_API_KEY is not configured")

        width, height = _parse_size(size)
        url = f"{_FAL_SYNC_BASE}/{self._model}"
        headers = {
            "Authorization": f"Key {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "prompt": prompt,
            "image_size": {"width": width, "height": height},
            "num_images": 1,
        }

        async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            body = resp.json()

            images = body.get("images") or []
            if not images:
                raise RuntimeError("Fal returned no images")

            image_url = images[0].get("url")
            content_type = images[0].get("content_type") or "image/jpeg"
            if not image_url:
                raise RuntimeError("Fal image entry missing url")

            img_resp = await client.get(image_url)
            img_resp.raise_for_status()
            data = img_resp.content

        logger.info(
            "fal_image_generated",
            model=self._model,
            bytes=len(data),
            content_type=content_type,
        )
        return ImageResult(data=data, content_type=content_type)
