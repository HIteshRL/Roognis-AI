from collections.abc import AsyncGenerator

import structlog
from groq import APIError as GroqAPIError
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


class GroqProvider(AbstractLLMProvider):
    def __init__(self, api_key: str) -> None:
        self._client = AsyncGroq(api_key=api_key)

    @property
    def provider_name(self) -> str:
        return "groq"

    async def complete(self, messages: list[LLMMessage], config: LLMConfig) -> LLMResponse:
        try:
            response = await self._client.chat.completions.create(
                model=config.model,
                messages=[{"role": m.role, "content": m.content} for m in messages],
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
            logger.error("groq_api_error", error=str(e), model=config.model)
            raise LLMError(f"LLM provider error: {e}") from e

    async def stream(
        self, messages: list[LLMMessage], config: LLMConfig
    ) -> AsyncGenerator[str, None]:
        try:
            stream = await self._client.chat.completions.create(
                model=config.model,
                messages=[{"role": m.role, "content": m.content} for m in messages],
                temperature=config.temperature,
                max_tokens=config.max_tokens,
                stream=True,
            )
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
