import asyncio

import structlog
from groq import APIConnectionError as GroqAPIConnectionError
from groq import APIError as GroqAPIError
from groq import APIStatusError as GroqAPIStatusError
from groq import AsyncGroq

from src.domain.exceptions import LLMError
from src.infrastructure.vision.base import AbstractVisionProvider

logger = structlog.get_logger(__name__)

_MAX_RETRIES = 2
_BASE_BACKOFF_SECONDS = 0.5
_RETRYABLE_STATUS_CODES = {408, 429, 500, 502, 503, 504}

_DEFAULT_OCR_PROMPT = (
    "You are an OCR engine for K-12 curriculum material. Transcribe ALL text "
    "visible in this image exactly as written, preserving reading order, "
    "headings, lists, and mathematical notation. Describe any diagram or figure "
    "in one short bracketed line, e.g. [Figure: labelled diagram of a plant cell]. "
    "Output only the transcription — no preamble, no commentary. If the image "
    "contains no legible text, output nothing."
)


def _is_retryable(exc: Exception) -> bool:
    if isinstance(exc, GroqAPIConnectionError):
        return True
    if isinstance(exc, GroqAPIStatusError):
        return exc.status_code in _RETRYABLE_STATUS_CODES
    return False


class GroqVisionProvider(AbstractVisionProvider):
    """
    Transcribes images to text using a Groq vision-capable model (Llama 4).

    Sends an OpenAI-style multimodal message (text prompt + image_url part).
    Retries only transient/transport errors; a non-retryable API error raises
    LLMError so the caller can fail open.
    """

    def __init__(
        self,
        api_key: str,
        model: str,
        temperature: float = 0.0,
        max_tokens: int = 4096,
    ) -> None:
        self._client = AsyncGroq(api_key=api_key)
        self._model = model
        self._temperature = temperature
        self._max_tokens = max_tokens

    @property
    def provider_name(self) -> str:
        return "groq-vision"

    async def extract_text(self, image_data_uri: str, prompt: str | None = None) -> str:
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt or _DEFAULT_OCR_PROMPT},
                    {"type": "image_url", "image_url": {"url": image_data_uri}},
                ],
            }
        ]

        last_error: Exception | None = None
        for attempt in range(_MAX_RETRIES + 1):
            try:
                response = await self._client.chat.completions.create(
                    model=self._model,
                    messages=messages,
                    temperature=self._temperature,
                    max_tokens=self._max_tokens,
                    stream=False,
                )
                return (response.choices[0].message.content or "").strip()
            except GroqAPIError as e:
                last_error = e
                if attempt < _MAX_RETRIES and _is_retryable(e):
                    backoff = _BASE_BACKOFF_SECONDS * (2**attempt)
                    logger.warning(
                        "groq_vision_retry",
                        attempt=attempt + 1,
                        backoff=backoff,
                        error=str(e),
                    )
                    await asyncio.sleep(backoff)
                    continue
                logger.error("groq_vision_error", error=str(e), model=self._model)
                raise LLMError(f"Vision provider error: {e}") from e
        raise LLMError(f"Vision provider error: {last_error}") from last_error
