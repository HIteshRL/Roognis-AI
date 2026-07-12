from src.config import Settings, get_settings
from src.infrastructure.storage.base import AbstractFileStorage
from src.infrastructure.storage.local_storage import LocalFileStorage
from src.infrastructure.storage.s3_storage import S3FileStorage


def get_file_storage(settings: Settings | None = None) -> AbstractFileStorage:
    settings = settings or get_settings()
    if settings.storage_provider == "s3":
        return S3FileStorage(
            bucket=settings.s3_bucket,
            endpoint_url=settings.s3_endpoint_url,
            region=settings.s3_region,
            access_key_id=settings.s3_access_key_id,
            secret_access_key=settings.s3_secret_access_key,
        )
    return LocalFileStorage(settings.storage_local_path)
