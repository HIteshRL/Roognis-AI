# Roognis AI — Operating Manual for Claude Sessions

## Project Overview

Roognis AI is an adaptive AI tutoring platform for K-12 students. It provides a conversational AI tutor powered by a Groq-hosted LLM (Llama 3.3 70B), with deep learning analytics that track mastery, misconceptions, behavioral patterns, and teaching history on a per-student, per-concept basis.

**The system learns from every conversation.** After each chat response is streamed, a background pipeline extracts concepts, updates mastery scores, detects misconceptions, and now (Phase 0.5) records intent classifications and concept-level teaching memory. All of this feeds back into the LLM system prompt the next time the student asks a question.

---

## Business Objective

Build an AI tutor that behaves like a human teacher: it remembers what it has explained before, notices when explanations aren't working, adapts its teaching style to the individual student, and guides the student along the optimal learning path through the curriculum.

---

## Tech Stack

### Backend (`apps/api`)
- **Runtime:** Python 3.12
- **Framework:** FastAPI 0.115.6 with async/await throughout
- **Database:** PostgreSQL (via asyncpg + SQLAlchemy 2.0 async ORM)
- **Migrations:** Alembic 1.14.0 (sequential numeric revisions: 001–006)
- **Cache/Rate limiting:** Redis (via redis[asyncio])
- **LLM:** Groq API — `llama-3.3-70b-versatile` (chat) and `llama-3.1-8b-instant` (extraction)
- **Embeddings:** fastembed (local) or OpenAI (configurable)
- **Vector Store:** Qdrant
- **Auth:** JWT via python-jose + passlib/bcrypt (Clerk on frontend)
- **Observability:** structlog + Prometheus (prometheus-fastapi-instrumentator)
- **Linting:** Ruff 0.8.4 (`ruff check --fix` before every commit)
- **Tests:** pytest-asyncio, factory-boy

### Frontend (`apps/web`)
- **Framework:** Next.js 15.1.3 (App Router, Turbopack in dev)
- **Language:** TypeScript
- **Auth:** Clerk (`@clerk/nextjs`)
- **State/Queries:** TanStack Query v5 + Zustand
- **UI Components:** Radix UI primitives + shadcn/ui patterns
- **Styling:** Tailwind CSS v4
- **Forms:** react-hook-form + zod
- **Markdown:** react-markdown + rehype-highlight + remark-gfm
- **Theme:** next-themes (dark/light)
- **Toast:** sonner
- **Icons:** lucide-react
- **Tests:** Vitest

### Monorepo
- **Tool:** Turborepo (`turbo.json`)
- **Package manager:** npm workspaces

---

## Project Architecture

```
Roognis AI
├── apps/
│   ├── api/              # FastAPI Python backend
│   └── web/              # Next.js 15 frontend
├── packages/             # Shared TypeScript packages
├── docs/                 # Architecture and developer docs
├── docker/               # Dockerfile(s)
└── docker-compose.yml    # Local dev infra (Postgres, Redis, Qdrant)
```

### Backend Clean Architecture

```
src/
├── domain/               # Pure Python — no I/O
│   ├── entities/         # Dataclasses (StudentProfile, MasteryRecord, ConceptMemory, ...)
│   ├── repositories/     # Abstract base classes (ABCs)
│   └── exceptions/       # Domain exceptions
├── application/
│   ├── services/         # Business logic (orchestrators, engines, analyzers)
│   ├── dtos/             # Pydantic request/response models
│   └── interfaces/       # dependencies.py — FastAPI DI wiring
├── infrastructure/
│   ├── database/
│   │   ├── models/       # SQLAlchemy ORM models
│   │   ├── repositories/ # Concrete repository implementations
│   │   ├── migrations/   # Alembic versions (001–006)
│   │   └── session.py    # Async session factory
│   ├── llm/              # LLM provider abstraction + Groq impl
│   ├── embeddings/       # Embedding provider abstraction + fastembed/openai
│   ├── vector/           # Vector store abstraction + Qdrant impl
│   ├── cache/            # Redis client
│   └── storage/          # Local file storage
└── presentation/
    └── api/v1/           # FastAPI route handlers
```

### Frontend Feature Structure

```
apps/web/
├── app/
│   ├── (auth)/           # Login, signup pages
│   └── (dashboard)/
│       ├── student/      # All student-facing routes
│       │   ├── page.tsx              # Dashboard
│       │   ├── mastery/              # Mastery records
│       │   ├── gaps/                 # Learning gaps
│       │   ├── graph/                # Knowledge graph
│       │   ├── learning-path/        # Learning path (Phase 0.5)
│       │   ├── skills/               # Skill profile (Phase 0.5)
│       │   ├── statistics/           # Analytics
│       │   └── timeline/             # Session timeline
│       └── (other routes)
├── features/
│   └── student/
│       └── components/   # All student UI components
├── lib/
│   └── api/
│       ├── client.ts     # Axios-based API client
│       └── student.ts    # All student API calls + TypeScript types
└── components/
    └── layout/
        └── Sidebar.tsx   # Main nav (add new routes here)
```

---

## Coding Standards

### Python
- All async — every service method that does I/O is `async def`
- Type annotations on all function signatures (Python 3.12 union syntax: `X | Y`)
- No comments unless the WHY is non-obvious
- Ruff enforced: `ruff check --fix apps/api/` before committing
- Line length: 100 characters
- `from __future__ import annotations` is NOT used — rely on Python 3.12 native types
- Pattern: dependency injection via constructor, never module-level globals in services

### TypeScript
- Strict mode enabled
- All API response types defined in `apps/web/lib/api/student.ts`
- TanStack Query for all server state — no `useState` + `useEffect` for API calls
- `'use client'` directive on all interactive components

---

## Naming Conventions

### Python
- Services: `NounVerbService` — `MasteryEngine`, `IntentEngine`, `LearningOrchestrator`
- Repositories: `AbstractNounRepository` (abstract), `NounRepository` (concrete)
- Entities: `PascalCase` dataclasses
- DB models: `NounModel` (suffix to distinguish from domain entities)
- Routes: snake_case path segments `/student/learning-path`

### Database Tables
- snake_case plural: `learning_sessions`, `concept_memory`, `student_profiles`
- FK columns: `user_id`, `concept_id` (suffix `_id`)
- Timestamps: `created_at`, `updated_at`, `last_taught`

### TypeScript
- Interfaces: `PascalCase` (`ConceptMemory`, `LearningPath`, `SkillProfile`)
- API functions: camelCase verb-noun (`getConceptMemory`, `getLearningPath`)
- Components: PascalCase (`LearningPathView`, `SkillsView`)

---

## Design Principles

1. **Fail-open everywhere in the learning pipeline.** The orchestrator wraps every step in try/except — a failure in concept extraction or mastery update MUST NOT affect the user's chat response. Log and continue.

2. **Do not redesign existing modules.** Always build on top of current implementations. Maintain backward compatibility. New services are added; existing service signatures get optional parameters with defaults.

3. **Modular and injectable.** Every service is constructed in `dependencies.py`. Routes only receive fully-assembled services via FastAPI `Depends()`. Services do not import each other directly — they receive dependencies through constructors.

4. **Single classification point.** The intent engine runs exactly once per request, in the route handler. The result is passed down to both consumers (ChatService and LearningOrchestrator) so nothing runs twice.

5. **Derive don't store when possible.** The skill profile is computed fresh from mastery + session data — no `skills` table needed. Teaching history is queried from `concept_memory` on each request.

6. **Domain logic in domain entities.** Properties like `needs_different_approach` and `success_rate` live on the `ConceptMemory` dataclass, not scattered across service code.

7. **All new tables require a migration.** Never modify DB models without adding an Alembic migration. Migrations are numbered sequentially: 001, 002, ..., 006. Never use `autogenerate` — write migrations explicitly.

---

## Environment Setup

### Prerequisites
- Python 3.12
- Node.js 20+
- Docker + Docker Compose

### Infrastructure (local)
```bash
docker-compose up -d   # starts Postgres, Redis, Qdrant
```

### Backend
```bash
cd apps/api
cp .env.example .env   # fill in API keys
pip install -e ".[dev]"
alembic upgrade head   # run all migrations 001–006
uvicorn src.main:app --reload --port 8000
```

### Frontend
```bash
cd apps/web
cp .env.local.example .env.local   # set NEXT_PUBLIC_API_URL, Clerk keys
npm install
npm run dev   # starts on :3000
```

### Required Environment Variables (Backend)
```
DATABASE_URL=postgresql+asyncpg://...
REDIS_URL=redis://localhost:6379
API_SECRET_KEY=<min 32 chars>
GROQ_API_KEY=<groq cloud key>
CLERK_SECRET_KEY=<from Clerk dashboard>
CLERK_PUBLISHABLE_KEY=<from Clerk dashboard>
```

---

## Build Commands

```bash
# Backend
ruff check --fix apps/api/        # lint + auto-fix
pytest apps/api/tests/ -v         # run all tests
alembic upgrade head               # apply pending migrations
alembic revision --rev-id 007 -m "description"  # create new migration

# Frontend
npm run type-check --workspace=apps/web
npm run build --workspace=apps/web
npm run test --workspace=apps/web
```

---

## Test Commands

```bash
# All tests
pytest apps/api/tests/ -v

# Specific service
pytest apps/api/tests/services/test_intent_engine.py -v
pytest apps/api/tests/services/test_skill_graph_service.py -v
pytest apps/api/tests/services/test_learning_path_service.py -v

# With coverage
pytest apps/api/tests/ --cov=src --cov-report=term-missing

# Current state: 156 passing, 3 pre-existing failures (bcrypt version conflict)
```

**Known pre-existing test failures (do not fix unless explicitly asked):**
- `test_register_success`, `test_login_success`, `test_login_wrong_password`
- Cause: `pyproject.toml` pins `bcrypt==3.2.2` but environment has bcrypt 4.x; passlib calls `bcrypt.__about__.__version__` which doesn't exist in 4.x
- Fix: upgrade to `bcrypt>=4.0.0` and `passlib>=1.7.5` in pyproject.toml

---

## Deployment Process

1. Docker Compose for local + staging
2. Production deployment: not yet implemented (see `docs/DEPLOYMENT.md` for planned approach)
3. Migrations must run before API starts: `alembic upgrade head`

---

## APIs and Integrations

### Backend REST API (FastAPI — port 8000)

All routes under `/api/v1/`:

| Route | Method | Description |
|-------|--------|-------------|
| `/auth/register` | POST | Register user |
| `/auth/login` | POST | JWT login |
| `/chat/stream` | POST | Streaming chat (SSE) |
| `/student/profile` | GET/POST | Student profile |
| `/student/sessions` | GET | Session history (includes `intent` field) |
| `/student/mastery` | GET | Mastery records |
| `/student/gaps` | GET | Active misconceptions/gaps |
| `/student/gaps/{id}/resolve` | POST | Mark gap resolved |
| `/student/recommendations` | GET | NextBestTopic recommendations |
| `/student/memory` | GET | Concept teaching memory (Phase 0.5) |
| `/student/learning-path` | GET | Learning path + frontier + coverage (Phase 0.5) |
| `/student/skills` | GET | Derived skill profile (Phase 0.5) |
| `/student/analytics` | GET | Learning analytics summary |
| `/knowledge/graph` | GET | Knowledge graph nodes/edges |
| `/documents/*` | CRUD | Document management (RAG) |
| `/rag/query` | POST | RAG query |
| `/search` | GET | Semantic search |

### External Integrations
- **Groq API** — LLM inference (chat + concept extraction)
- **Clerk** — Frontend authentication (webhooks sync user to backend)
- **Qdrant** — Vector database for RAG
- **fastembed** — Local embedding generation (no API call)

---

## Database Schema (Key Tables)

```
users                     — id, email, hashed_password, role
student_profiles          — user_id, grade, subjects, current_chapter,
                            confidence_score, learning_velocity, behavioral_signals (JSONB)
learning_sessions         — user_id, conversation_id, subject, chapter, grade,
                            question, primary_concept, concepts_discussed, bloom_level,
                            difficulty_level, misconceptions, intent, token_count,
                            duration_ms, created_at
concept_nodes             — id, name, subject, chapter, bloom_level, difficulty, grade
concept_edges             — source_id, target_id, relationship_type (prerequisite etc.)
mastery_records           — user_id, concept_id, concept_name, score (0-100), label,
                            interaction_count, last_updated
learning_gaps             — user_id, concept_id, concept_name, severity, reason,
                            confidence, occurrence_count, is_resolved
concept_memory            — user_id, concept_id, concept_name, times_taught,
                            successful_approaches, failed_approaches, last_approach,
                            teaching_notes (JSONB), last_taught  [Phase 0.5]
conversations             — id, user_id, title, created_at
messages                  — conversation_id, role, content, created_at
knowledge_bases           — id, name, subject, grade
documents                 — kb_id, filename, status, chunk_count
chunks                    — doc_id, content, embedding_id, metadata
```

Migration history: 001 (users+auth) → 002 (knowledge/RAG) → 003 (curriculum RAG) → 004 (learning engine) → 005 (behavioral signals) → 006 (Phase 0.5: intent + concept_memory)

---

## Security Considerations

- JWT tokens signed with `API_SECRET_KEY` (min 32 chars)
- Clerk handles social auth on frontend; backend validates Clerk JWTs
- Rate limiting on all routes via Redis (chat: 20/min, auth: 10/min, default: 100/min)
- SQL injection impossible — SQLAlchemy ORM with parameterized queries only
- No raw SQL strings anywhere
- CORS configured explicitly (`cors_origins` in Settings)
- Admin routes protected by `require_admin` dependency
- User data isolation: every DB query filters by `user_id` from the authenticated JWT

---

## Performance Considerations

- All DB access is async (asyncpg) — no blocking I/O in request handlers
- Learning pipeline runs as `BackgroundTask` after response is fully streamed — zero added latency
- Intent classification is synchronous + zero-latency (pure rule matching, no I/O)
- Concept memory: `get_or_create` pattern avoids N+1 via single upsert
- LearnerContextService uses `_MAX_STRUGGLING_CONCEPTS = 3` to cap system prompt size
- Teaching history capped at 5 notes per concept (`teaching_notes[-5:]`)
- LLM context capped at `_MAX_WEAK_CONCEPTS = 5`, `_MAX_ACTIVE_GAPS = 5`, `_MAX_STRENGTHS = 3`
- Redis response cache for RAG queries (prevents duplicate LLM calls for identical questions)
- Qdrant vector search with configurable `top_k` and `score_threshold`

---

## Important Architectural Decisions

1. **IntentEngine is stateless** — classify() has no constructor args, no I/O. Instantiated fresh per request via `get_intent_engine()` dependency. No singleton needed since it holds no state.

2. **Skill profile is never persisted** — SkillGraphService has no DB access. It derives skill data freshly from mastery_records + sessions on each `/student/skills` call. This avoids a skills table and keeps skill data always current.

3. **ConceptMemoryService typed as `Any` in LearnerContextService** — to avoid circular imports between services in the same package. Typed as `concept_memory_svc=None` with a comment. FastAPI resolves it at runtime.

4. **Migration 006 uses `server_default="unknown"`** — intent column on learning_sessions has a server_default so existing rows are not null and no backfill migration is needed.

5. **Kahn's algorithm for learning order** — chosen over DFS topological sort because it naturally handles disconnected subgraphs and cycles by appending unprocessed nodes at the end (fail-open).

6. **Rule-based intent over LLM-based** — avoids 500ms–2s pre-call latency. Accuracy trade-off accepted; misfires are harmless (a wrong intent directive rarely breaks the response).

---

## Things Future Claude Sessions Must Always Remember

- **DO NOT redesign existing modules.** All new work must build on top of current implementations.
- **All new services go in `apps/api/src/application/services/`** and must be wired in `dependencies.py`.
- **New DB tables require a migration** — next one is `007`. Never skip.
- **Ruff must pass** before committing: `ruff check --fix apps/api/` then `ruff check apps/api/` to verify.
- **The 3 bcrypt test failures are pre-existing** — do not report them as newly introduced.
- **The learning pipeline is background-only** — `LearningOrchestrator.process()` is always called as `BackgroundTask`, never awaited in the request path.
- **Frontend API types live in `apps/web/lib/api/student.ts`** — add new interfaces there for any new backend response fields.
- **Sidebar nav is in `apps/web/components/layout/Sidebar.tsx`** — add new student routes to `learningNavItems`.
