from abc import ABC, abstractmethod


class AbstractVisionProvider(ABC):
    """
    Contract for vision models that transcribe an image to text (OCR).

    Application services depend on this interface, never on a concrete
    provider. Implementations receive a base64 ``data:`` URI and return the
    transcribed text, or an empty string when nothing can be read.
    """

    @abstractmethod
    async def extract_text(self, image_data_uri: str, prompt: str | None = None) -> str: ...

    @property
    @abstractmethod
    def provider_name(self) -> str: ...
