from fastapi import APIRouter, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated
from fastapi import Depends

from src.config import get_settings
from src.infrastructure.cache.redis_client import get_redis
from src.infrastructure.database.session import get_db
from src.infrastructure.llm.factory import get_llm_provider
from src.presentation.api.response import ok

router = APIRouter(tags=["System"])

import time

_start_time = time.time()


@router.get("/health")
async def health(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    db_ok = False
    redis_ok = False

    try:
        await db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        pass

    try:
        redis = await get_redis()
        await redis.ping()
        redis_ok = True
    except Exception:
        pass

    overall = "healthy" if db_ok and redis_ok else "degraded"
    return ok(
        {
            "status": overall,
            "database": "up" if db_ok else "down",
            "cache": "up" if redis_ok else "down",
            "uptime_seconds": round(time.time() - _start_time, 1),
        },
        request_id=request.state.request_id,
    )


@router.get("/version")
async def version(request: Request):
    settings = get_settings()
    return ok(
        {"version": settings.app_version, "env": settings.app_env},
        request_id=request.state.request_id,
    )
