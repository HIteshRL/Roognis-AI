# Architecture — Phase 0.1

## Clean Architecture

Every layer has a single responsibility. Dependencies point inward only.

```
┌─────────────────────────────────────────────────────┐
│  Presentation (FastAPI routes, Next.js pages)        │
│  ↓ depends on                                        │
│  Application (Services, DTOs, Interfaces)            │
│  ↓ depends on                                        │
│  Domain (Entities, Repository Interfaces, Exceptions)│
│  ↑ implemented by                                    │
│  Infrastructure (DB, Redis, LLM, Logging)            │
└─────────────────────────────────────────────────────┘
```

**Rules enforced:**
- Routes call Services only. No DB access in routes.
- Services call Repository Interfaces only. No SQLAlchemy in services.
- Domain has zero external dependencies.
- Infrastructure depends on Domain interfaces, never the reverse.

## Backend Module Map

```
apps/api/src/
  config.py                       # Pydantic Settings — one source of truth
  main.py                         # FastAPI app assembly
  presentation/api/v1/            # Route handlers (thin, no logic)
    auth.py  users.py  chat.py  system.py
  application/
    services/                     # Business logic
      auth_service.py
      user_service.py
      chat_service.py
    dtos/                         # Pydantic request/response models
    interfaces/dependencies.py    # FastAPI DI container
  domain/
    entities/                     # Pure Python dataclasses
    repositories/                 # Abstract interfaces (ABC)
    exceptions/                   # Typed domain exceptions
  infrastructure/
    database/
      base.py                     # SQLAlchemy Base + mixins
      session.py                  # Async session factory
      models/                     # ORM models
      repositories/               # Concrete repository implementations
      migrations/                 # Alembic
    llm/
      base.py                     # AbstractLLMProvider contract
      groq_provider.py            # Groq implementation
      factory.py                  # Provider selection
      prompt_loader.py            # DB-backed prompt templates
    middleware/                   # All 7 middleware components
    cache/redis_client.py         # Async Redis client
    logging/setup.py              # structlog JSON setup
```

## Frontend Module Map

```
apps/web/
  app/                            # Next.js App Router
    (auth)/                       # Public auth pages (no sidebar)
    (dashboard)/                  # Protected pages (with sidebar)
  features/                       # Feature-based, not component-based
    auth/        → LoginForm, RegisterForm, ForgotPasswordForm
    chat/        → ChatView, MessageBubble, ChatInput, ConversationList
    dashboard/   → DashboardView
    profile/     → ProfileView
    settings/    → SettingsView
  components/
    ui/          → shadcn/ui primitives (no business logic)
    layout/      → Sidebar, ThemeProvider
  lib/
    api/         → Typed fetch wrappers (auth, chat, user)
    stores/      → Zustand (auth.store, chat.store)
    validators/  → Zod schemas
    providers/   → QueryProvider (TanStack Query)
```

## LLM Abstraction

```
AbstractLLMProvider (base.py)
    ↓ implemented by
GroqProvider (groq_provider.py)
    ↓ selected by
factory.get_llm_provider()
    ↓ consumed by
ChatService (application layer)
```

To add a new provider: implement `AbstractLLMProvider`, register in `factory.py`. Zero changes to ChatService.

## Streaming Architecture

```
User → POST /api/v1/chat
         ↓
    ChatService.stream_response()
         ↓
    AbstractLLMProvider.stream()  (async generator)
         ↓
    FastAPI StreamingResponse (SSE)
         ↓
    Frontend fetch + ReadableStream
         ↓
    ChatStore.appendStreamChunk()
         ↓
    StreamingMessage component
```

SSE format:
```
data: {"type":"meta","conversation_id":"..."}
data: {"type":"chunk","content":"Hello"}
data: {"type":"done","message_id":"..."}
```

## Middleware Stack (outermost → innermost)

1. SecurityHeadersMiddleware — adds X-Content-Type-Options, X-Frame-Options etc.
2. RateLimitMiddleware — Redis-backed per-IP limits
3. RequestLoggingMiddleware — structured JSON logs per request
4. RequestIDMiddleware — injects unique `request_id` into context
5. CORSMiddleware — configurable origins
6. Route handlers
7. Exception handlers — translate all exceptions to standard JSON envelopes

## API Response Envelope

All responses use this shape (success or error):

```json
{
  "success": true,
  "data": {},
  "message": "",
  "request_id": "req_abc123"
}
```

Errors:
```json
{
  "success": false,
  "error": {
    "code": "UNAUTHORIZED",
    "message": "Human-readable message",
    "details": {}
  },
  "request_id": "req_abc123"
}
```
