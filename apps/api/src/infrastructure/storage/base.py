from abc import ABC, abstractmethod


class AbstractFileStorage(ABC):
    @abstractmethod
    async def save(self, file_bytes: bytes, destination: str) -> str:
        """Save bytes to destination path. Returns the resolved storage path."""
        ...

    @abstractmethod
    async def read(self, storage_path: str) -> bytes: ...

    @abstractmethod
    async def delete(self, storage_path: str) -> None: ...

    @abstractmethod
    async def exists(self, storage_path: str) -> bool: ...
