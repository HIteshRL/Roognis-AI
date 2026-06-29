# Development Guide

## Prerequisites

- Node.js ≥ 20
- pnpm ≥ 9
- Python 3.12
- Docker + Docker Compose
- PostgreSQL 16 (or use Docker)
- Redis 7 (or use Docker)

## Setup

```bash
# Clone repo
git clone <repo>
cd roognis-ai

# Copy environment
cp .env.example .env
# Edit .env — at minimum set:
#   CLERK_SECRET_KEY, NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY
#   GROQ_API_KEY
#   API_SECRET_KEY (any 32+ char string)

# Install frontend deps
pnpm install

# Install backend deps
cd apps/api
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

## Running Locally

### Backend
```bash
cd apps/api
# Run DB migrations
alembic upgrade head
# Seed prompt templates
python ../../scripts/seed.py
# Start API
uvicorn src.main:app --reload --port 8000
```

### Frontend
```bash
# From repo root
pnpm --filter @roognis/web dev
```

### Full stack (Docker)
```bash
docker compose up --build
```

## Testing

```bash
# Backend unit + API tests
cd apps/api
pytest --cov=src --cov-report=term-missing

# Frontend type checking
pnpm --filter @roognis/web type-check
```

## Code Style

**Backend:**
```bash
cd apps/api
ruff check src/
ruff format src/
```

**Frontend:**
```bash
pnpm --filter @roognis/web lint
```

## Adding a New LLM Provider

1. Implement `AbstractLLMProvider` in `apps/api/src/infrastructure/llm/`
2. Register it in `factory.py`
3. Done — ChatService requires no changes

## Adding a New API Endpoint

1. Add route handler in `presentation/api/v1/`
2. Create DTOs in `application/dtos/`
3. Implement logic in `application/services/`
4. Add repository method to domain interface + infrastructure implementation
5. Wire dependency in `application/interfaces/dependencies.py`

## Architecture Constraints

- Never put business logic in route handlers
- Never import SQLAlchemy inside application or domain layers
- All responses must use the `ok()` or `paginated()` helpers
- Every domain exception must be a subclass of `DomainException`
