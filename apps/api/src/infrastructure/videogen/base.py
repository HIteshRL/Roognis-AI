from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class VideoResult:
    data: bytes
    content_type: str  # "video/mp4"


class AbstractVideoGenerator(ABC):
    """
    Contract for text-to-video providers.
    generate() is synchronous-blocking under the hood (torch); callers run it
    in an executor so it never blocks the event loop.
    """

    @abstractmethod
    def generate(
        self, prompt: str, num_frames: int = 97, fps: int = 24
    ) -> VideoResult: ...

    @property
    @abstractmethod
    def provider_name(self) -> str: ...
