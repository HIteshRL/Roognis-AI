import httpx
import structlog

from src.infrastructure.videogen.base import AbstractVideoGenerator, VideoResult

logger = structlog.get_logger(__name__)

_FAL_SYNC_BASE = "https://fal.run"
_TIMEOUT_SECONDS = 300.0   # text-to-video is slower than images


class FalVideoGenerator(AbstractVideoGenerator):
    """Text-to-video via Fal's hosted LTX-Video endpoint.

    Lets the platform generate explainer clips without a self-hosted GPU — the
    heavy inference runs on Fal. Synchronous (httpx.Client) to match the
    AbstractVideoGenerator contract; callers already run generate() in an
    executor, so blocking on the HTTP call is fine. Raises on failure so the
    media-job pipeline can fail-open.
    """

    def __init__(self, api_key: str, model: str = "fal-ai/ltx-video") -> None:
        self._api_key = api_key
        self._model = model

    @property
    def provider_name(self) -> str:
        return "fal"

    def generate(self, prompt: str, num_frames: int = 97, fps: int = 24) -> VideoResult:
        if not self._api_key:
            raise RuntimeError("FAL_API_KEY is not configured")

        url = f"{_FAL_SYNC_BASE}/{self._model}"
        headers = {
            "Authorization": f"Key {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {"prompt": prompt, "num_frames": num_frames, "fps": fps}

        with httpx.Client(timeout=_TIMEOUT_SECONDS) as client:
            resp = client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            body = resp.json()

            video = body.get("video") or {}
            video_url = video.get("url")
            if not video_url:
                raise RuntimeError("Fal returned no video url")

            content_type = video.get("content_type") or "video/mp4"
            clip = client.get(video_url)
            clip.raise_for_status()
            data = clip.content

        logger.info("fal_video_generated", model=self._model, bytes=len(data))
        return VideoResult(data=data, content_type=content_type)
