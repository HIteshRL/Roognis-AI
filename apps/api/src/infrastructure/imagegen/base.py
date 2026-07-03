from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ImageResult:
    data: bytes
    content_type: str  # e.g. "image/png", "image/jpeg"


class AbstractImageGenerator(ABC):
    """
    Contract for text-to-image providers.
    Application services depend on this interface, never on concrete providers.
    """

    @abstractmethod
    async def generate(self, prompt: str, size: str = "1024x1024") -> ImageResult: ...

    @property
    @abstractmethod
    def provider_name(self) -> str: ...
