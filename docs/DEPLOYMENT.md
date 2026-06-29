# Deployment Guide

## Docker Compose (recommended for Phase 0.1)

```bash
# Build and start the full stack
docker compose up --build -d

# Check status
docker compose ps

# View logs
docker compose logs -f api
docker compose logs -f web

# Stop
docker compose down
```

Services exposed:
- `http://localhost:3000` → Next.js frontend
- `http://localhost:8000` → FastAPI backend
- `http://localhost:80` → Nginx reverse proxy (routes both)

## Required Environment Variables

Copy `.env.example` → `.env` and fill in:

| Variable | Required | Notes |
|----------|----------|-------|
| `API_SECRET_KEY` | Yes | Min 32 chars, random |
| `GROQ_API_KEY` | Yes | From console.groq.com |
| `CLERK_SECRET_KEY` | Yes | From Clerk dashboard |
| `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` | Yes | From Clerk dashboard |
| `POSTGRES_PASSWORD` | Yes | Any secure password |

All other variables have safe defaults for local development.

## First-Run Sequence

The `api` container automatically:
1. Runs `alembic upgrade head` (creates all 10 tables)
2. Runs `scripts/seed.py` (inserts default prompt templates)
3. Starts uvicorn

## Production Checklist

- [ ] Set `APP_ENV=production` (disables /docs, /redoc, /openapi.json)
- [ ] Use strong `API_SECRET_KEY` (generated, not guessed)
- [ ] Set `CORS_ORIGINS` to your actual domain
- [ ] Enable HTTPS (Nginx + Let's Encrypt or cloud load balancer)
- [ ] Set `LOG_FORMAT=json` for Grafana/ELK ingestion
- [ ] Configure `POSTGRES_PASSWORD` with a secrets manager
- [ ] Point `DATABASE_URL` to a managed PostgreSQL instance
- [ ] Point `REDIS_URL` to a managed Redis instance
- [ ] Set resource limits on Docker containers

## Monitoring

The `/api/v1/health` endpoint returns:
```json
{ "status": "healthy", "database": "up", "cache": "up", "uptime_seconds": 120 }
```

Configure your load balancer or health probe to hit this endpoint.

Structured JSON logs (stdout) are Grafana/ELK compatible out of the box.
Each log line includes `request_id` for distributed tracing.
