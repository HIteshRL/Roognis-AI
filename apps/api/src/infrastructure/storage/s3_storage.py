"""S3-compatible object storage — covers AWS S3, Cloudflare R2, and MinIO.

The provider is selected purely by endpoint_url: empty targets AWS, an R2 or
MinIO URL targets those. boto3 is blocking, so every call runs in a worker
thread via asyncio.to_thread.
"""
import asyncio
from functools import lru_cache

from src.infrastructure.storage.base import AbstractFileStorage


@lru_cache(maxsize=4)
def _make_client(
    endpoint_url: str, region: str, access_key_id: str, secret_access_key: str
):
    import boto3  # imported lazily so local-storage deployments don't need it

    return boto3.client(
        "s3",
        endpoint_url=endpoint_url or None,
        region_name=region or None,
        aws_access_key_id=access_key_id or None,
        aws_secret_access_key=secret_access_key or None,
    )


class S3FileStorage(AbstractFileStorage):
    def __init__(
        self,
        bucket: str,
        endpoint_url: str = "",
        region: str = "auto",
        access_key_id: str = "",
        secret_access_key: str = "",
    ) -> None:
        if not bucket:
            raise ValueError("S3 storage requires a bucket name (S3_BUCKET)")
        self._bucket = bucket
        self._client = _make_client(endpoint_url, region, access_key_id, secret_access_key)

    async def save(self, file_bytes: bytes, destination: str) -> str:
        key = destination.replace("\\", "/").lstrip("/")
        await asyncio.to_thread(
            self._client.put_object, Bucket=self._bucket, Key=key, Body=file_bytes
        )
        return key

    async def read(self, storage_path: str) -> bytes:
        response = await asyncio.to_thread(
            self._client.get_object, Bucket=self._bucket, Key=storage_path
        )
        return await asyncio.to_thread(response["Body"].read)

    async def delete(self, storage_path: str) -> None:
        await asyncio.to_thread(
            self._client.delete_object, Bucket=self._bucket, Key=storage_path
        )

    async def exists(self, storage_path: str) -> bool:
        try:
            await asyncio.to_thread(
                self._client.head_object, Bucket=self._bucket, Key=storage_path
            )
            return True
        except Exception:
            return False
