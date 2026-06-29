import structlog
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from src.infrastructure.cache.redis_client import get_redis

logger = structlog.get_logger(__name__)

# Paths that have their own stricter limits
_CHAT_PATH = "/api/v1/chat"
_AUTH_PATH = "/api/v1/auth"


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, default_limit: int, chat_limit: int, auth_limit: int, window: int):
        super().__init__(app)
        self._default = default_limit
        self._chat = chat_limit
        self._auth = auth_limit
        self._window = window

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        path = request.url.path

        if path.startswith(_CHAT_PATH):
            limit = self._chat
            scope = "chat"
        elif path.startswith(_AUTH_PATH):
            limit = self._auth
            scope = "auth"
        else:
            limit = self._default
            scope = "default"

        ip = request.client.host if request.client else "unknown"
        key = f"rl:{scope}:{ip}"

        try:
            redis = await get_redis()
            count_bytes = await redis.get(key)
            count = int(count_bytes) if count_bytes else 0

            if count >= limit:
                logger.warning("rate_limit_exceeded", ip=ip, scope=scope, count=count)
                request_id = getattr(request.state, "request_id", "unknown")
                return JSONResponse(
                    status_code=429,
                    content={
                        "success": False,
                        "error": {
                            "code": "RATE_LIMITED",
                            "message": "Too many requests. Please try again later.",
                            "details": {"retry_after": self._window},
                        },
                        "request_id": request_id,
                    },
                    headers={"Retry-After": str(self._window)},
                )

            pipe = redis.pipeline()
            pipe.incr(key)
            pipe.expire(key, self._window)
            await pipe.execute()

        except Exception:
            # Redis unavailable — fail open to avoid blocking all traffic
            logger.error("rate_limit_redis_error", exc_info=True)

        return await call_next(request)
