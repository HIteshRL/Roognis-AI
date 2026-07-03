import asyncio
from collections.abc import AsyncGenerator

import structlog
from groq import APIConnectionError as GroqAPIConnectionError
from groq import APIError as GroqAPIError
from groq import APIStatusError as GroqAPIStatusError
from groq import AsyncGroq

from src.domain.exceptions import LLMError
from src.infrastructure.llm.base import (
    AbstractLLMProvider,
    LLMConfig,
    LLMMessage,
    LLMResponse,
    LLMUsage,
)

logger = structlog.get_logger(__name__)

_MAX_RETRIES = 2
_BASE_BACKOFF_SECONDS = 0.5
_RETRYABLE_STATUS_CODES = {408, 429, 500, 502, 503, 504}


def _is_retryable(exc: Exception) -> bool:
    if isinstance(exc, GroqAPIConnectionError):
        return True
    if isinstance(exc, GroqAPIStatusError):
        return exc.status_code in _RETRYABLE_STATUS_CODES
    return False


def _render_message(m: LLMMessage) -> dict:
    """Render an LLMMessage into the Groq wire format.

    Text-only messages keep a plain string content (backward compatible).
    Messages carrying images use the multimodal content-parts array that
    Groq's vision models expect.
    """
    if not m.has_images:
        return {"role": m.role, "content": m.content}
    parts: list[dict] = []
    if m.content:
        parts.append({"type": "text", "text": m.content})
    for image_url in m.images or []:
        parts.append({"type": "image_url", "image_url": {"url": image_url}})
    return {"role": m.role, "content": parts}


def _render_messages(messages: list[LLMMessage]) -> list[dict]:
    return [_render_message(m) for m in messages]


class GroqProvider(AbstractLLMProvider):
    def __init__(self, api_key: str) -> None:
        self._client = AsyncGroq(api_key=api_key)

    @property
    def provider_name(self) -> str:
        return "groq"

    async def complete(self, messages: list[LLMMessage], config: LLMConfig) -> LLMResponse:
        last_error: Exception | None = None
        for attempt in range(_MAX_RETRIES + 1):
            try:
                response = await self._client.chat.completions.create(
                    model=config.model,
                    messages=_render_messages(messages),
                    temperature=config.temperature,
                    max_tokens=config.max_tokens,
                    stream=False,
                )
                usage = None
                if response.usage:
                    usage = LLMUsage(
                        prompt_tokens=response.usage.prompt_tokens,
                        completion_tokens=response.usage.completion_tokens,
                        total_tokens=response.usage.total_tokens,
                    )
                return LLMResponse(
                    content=response.choices[0].message.content or "",
                    model=response.model,
                    usage=usage,
                )
            except GroqAPIError as e:
                last_error = e
                if attempt < _MAX_RETRIES and _is_retryable(e):
                    backoff = _BASE_BACKOFF_SECONDS * (2**attempt)
                    logger.warning(
                        "groq_retry", attempt=attempt + 1, backoff=backoff, error=str(e)
                    )
                    await asyncio.sleep(backoff)
                    continue
                logger.error("groq_api_error", error=str(e), model=config.model)
                raise LLMError(f"LLM provider error: {e}") from e
        raise LLMError(f"LLM provider error: {last_error}") from last_error

    async def stream(
        self, messages: list[LLMMessage], config: LLMConfig
    ) -> AsyncGenerator[str, None]:
        # Retry only covers establishing the stream — once tokens have started
        # flowing to the client we cannot safely retry mid-response.
        stream = None
        last_error: Exception | None = None
        for attempt in range(_MAX_RETRIES + 1):
            try:
                stream = await self._client.chat.completions.create(
                    model=config.model,
                    messages=_render_messages(messages),
                    temperature=config.temperature,
                    max_tokens=config.max_tokens,
                    stream=True,
                )
                break
            except GroqAPIError as e:
                last_error = e
                if attempt < _MAX_RETRIES and _is_retryable(e):
                    backoff = _BASE_BACKOFF_SECONDS * (2**attempt)
                    logger.warning(
                        "groq_stream_retry", attempt=attempt + 1, backoff=backoff, error=str(e)
                    )
                    await asyncio.sleep(backoff)
                    continue
                logger.error("groq_stream_error", error=str(e), model=config.model)
                raise LLMError(f"LLM stream error: {e}") from e

        if stream is None:
            raise LLMError(f"LLM stream error: {last_error}") from last_error

        try:
            async for chunk in stream:
                delta = chunk.choices[0].delta.content
                if delta:
                    yield delta
        except GroqAPIError as e:
            logger.error("groq_stream_error", error=str(e), model=config.model)
            raise LLMError(f"LLM stream error: {e}") from e

    async def health_check(self) -> bool:
        try:
            await self._client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=1,
            )
            return True
        except Exception:
            return False
