from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError

from src.config import get_settings
from src.domain.exceptions import DomainException
from src.infrastructure.cache.redis_client import close_redis
from src.infrastructure.logging.setup import configure_logging
from src.infrastructure.middleware.error_handler import (
    domain_exception_handler,
    request_validation_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from src.infrastructure.middleware.logging import RequestLoggingMiddleware
from src.infrastructure.middleware.rate_limit import RateLimitMiddleware
from src.infrastructure.middleware.request_id import RequestIDMiddleware
from src.infrastructure.middleware.security_headers import SecurityHeadersMiddleware
from src.presentation.api.router import api_router

settings = get_settings()
configure_logging(settings.log_level, settings.log_format)
logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        "startup", app=settings.app_name, version=settings.app_version, env=settings.app_env
    )
    yield
    await close_redis()
    logger.info("shutdown", app=settings.app_name)


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
    openapi_url="/openapi.json" if not settings.is_production else None,
    lifespan=lifespan,
)

# ── Middleware (registration order = outermost first) ─────────────────────────
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    RateLimitMiddleware,
    default_limit=settings.rate_limit_default,
    chat_limit=settings.rate_limit_chat,
    auth_limit=settings.rate_limit_auth,
    window=settings.rate_limit_window_seconds,
)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-Response-Time"],
)

# ── Exception handlers ────────────────────────────────────────────────────────
app.add_exception_handler(DomainException, domain_exception_handler)  # type: ignore[arg-type]
app.add_exception_handler(RequestValidationError, request_validation_exception_handler)  # type: ignore[arg-type]
app.add_exception_handler(ValidationError, validation_exception_handler)  # type: ignore[arg-type]
app.add_exception_handler(Exception, unhandled_exception_handler)

# ── Routes ────────────────────────────────────────────────────────────────────
app.include_router(api_router)
