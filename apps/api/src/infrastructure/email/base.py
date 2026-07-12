from abc import ABC, abstractmethod


class AbstractEmailProvider(ABC):
    @abstractmethod
    async def send(self, to: str, subject: str, body: str) -> None: ...
