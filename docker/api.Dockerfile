FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

FROM base AS deps
COPY apps/api/pyproject.toml .
RUN pip install hatch && hatch env create && pip install -e ".[dev]" || true
RUN pip install fastapi uvicorn[standard] pydantic pydantic-settings sqlalchemy[asyncio] asyncpg alembic redis python-jose passlib httpx groq python-multipart structlog python-dotenv

FROM deps AS runtime
COPY apps/api/ .

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health')"

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
