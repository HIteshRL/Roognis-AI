from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from dataclasses import dataclass


@dataclass
class LLMMessage:
    role: str  # 'user' | 'assistant' | 'system'
    content: str


@dataclass
class LLMConfig:
    model: str
    temperature: float = 0.7
    max_tokens: int = 4096
    stream: bool = True


@dataclass
class LLMUsage:
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


@dataclass
class LLMResponse:
    content: str
    model: str
    usage: LLMUsage | None = None


class AbstractLLMProvider(ABC):
    """
    All LLM providers must implement this contract.
    Application services depend on this interface, never on concrete providers.
    """

    @abstractmethod
    async def complete(self, messages: list[LLMMessage], config: LLMConfig) -> LLMResponse: ...

    @abstractmethod
    async def stream(
        self, messages: list[LLMMessage], config: LLMConfig
    ) -> AsyncGenerator[str, None]: ...

    @abstractmethod
    async def health_check(self) -> bool: ...

    @property
    @abstractmethod
    def provider_name(self) -> str: ...
