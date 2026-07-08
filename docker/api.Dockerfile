FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

FROM base AS runtime
# Install straight from pyproject.toml (single source of truth — includes
# bcrypt==4.0.1, qdrant-client, fastembed, jose/passlib extras, prometheus).
# Editable so `src` resolves to the real tree (keeps prompt/data files intact).
# No `|| true`: a dependency failure must fail the build, not ship a broken image.
COPY apps/api/ .
RUN pip install --upgrade pip && pip install -e .

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health')"

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
