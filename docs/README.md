# Roognis AI

**AI-native Learning Operating System** — Phase 0.1

Roognis AI is a personalized, measurable, AI-driven education platform. This repository contains Phase 0.1: the complete frontend-backend foundation.

## Quick Start

```bash
# 1. Copy environment config
cp .env.example .env
# Fill in required values (see docs/SETUP.md)

# 2. Start the full stack
docker compose up --build

# 3. Open the app
open http://localhost:3000
```

## What's Included (Phase 0.1)

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Frontend | Next.js 15, React, TypeScript, Tailwind, shadcn/ui | All UI |
| Backend | FastAPI, Python 3.12 | REST API + SSE streaming |
| Database | PostgreSQL 16 | Persistent storage |
| Cache | Redis 7 | Rate limiting |
| Auth | Clerk | Identity provider |
| LLM | Groq API | Inference |
| Container | Docker Compose | Full stack |

## User Journey

1. Open `http://localhost:3000`
2. Register an account
3. Login
4. Access Dashboard
5. Open Chat
6. Send a message → receive a streaming LLM response
7. View chat history in the sidebar
8. Update profile and settings
9. Logout

## Documentation

- [Architecture](ARCHITECTURE.md)
- [Database Schema](DATABASE.md)
- [API Reference](API.md)
- [Development Guide](DEVELOPMENT.md)
- [Deployment Guide](DEPLOYMENT.md)

## Phase Roadmap

```
Phase 0.1  ← You are here
Phase 0.2  RAG & Context Intelligence
Phase 0.3  Psychographic & Learner Profile Engine
Phase 0.4  Learning Intelligence Engine
Phase 0.5  Multi-Persona Platform
Phase 0.6  Multimodal Intelligence
Phase 0.7  Beta Deployment
```
