import os

import aiofiles

from src.infrastructure.storage.base import AbstractFileStorage


class LocalFileStorage(AbstractFileStorage):
    def __init__(self, base_path: str) -> None:
        self._base = base_path
        os.makedirs(base_path, exist_ok=True)

    def _resolve(self, path: str) -> str:
        return os.path.join(self._base, path)

    async def save(self, file_bytes: bytes, destination: str) -> str:
        full_path = self._resolve(destination)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        async with aiofiles.open(full_path, "wb") as f:
            await f.write(file_bytes)
        return full_path

    async def read(self, storage_path: str) -> bytes:
        async with aiofiles.open(storage_path, "rb") as f:
            return await f.read()

    async def delete(self, storage_path: str) -> None:
        try:
            os.remove(storage_path)
        except FileNotFoundError:
            pass

    async def exists(self, storage_path: str) -> bool:
        return os.path.exists(storage_path)
