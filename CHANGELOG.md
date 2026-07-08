# Changelog — Roognis AI

All notable changes are documented here in reverse chronological order.

---

## [Unreleased] — 2026-07-07 — Phases 0.6–0.9, MVP Hardening, 5-Kid Demo, Web-Boot & Chat Fixes

**Commits:** `097efbb..32ce112` (15 commits) · **Branch:** `feat/multi-chat-cag` (pushed to origin)

Consolidated entry — this stretch spans several phases plus two directed hardening passes; see `HANDOFF.md` for full narrative and `git log --oneline 097efbb..HEAD` for the exact commit list.

### Features Added

- **Multi-conversation chat + CAG retrieval pipeline** (Phase 0.6).
- **Generative multimodal tutoring (v0.71)** — image generation (Fal, default-on per answer) and on-demand video generation (self-hosted LTX), `media_jobs` table, 3-pane Classroom/NotebookLM chat layout.
- **Mobile app (Expo)** — standalone React Native client against the hosted backend, custom JWT auth.
- **School B2B2C (Phase 0.8)** — `users.role`, schools, school_members, classrooms (join codes), enrollments, syllabus_items (migration 011); teacher portal + student "My Classes" on web and mobile.
- **Caching Engine + FAQ Intelligence (Phase 0.9, ADR-012)** — query normalization, semantic hashing, hot-query detection, scoped cache invalidation, FAQ auto-promotion (migration 012).
- **Parent Portal (Phase 0.9, ADR-013)** — consent-based guardian linking via 8-char codes, read-only child overview (migration 013).
- **Role selection at signup** — `RegisterRequest.role: Literal["student","parent","teacher"]`; previously every signup hardcoded to `student`, leaving teacher/parent dashboards unreachable for new accounts.
- **Teacher Classroom Analytics** — batch `GROUP BY` repository methods (no N+1), `ClassroomAnalyticsService`, `GET /school/classrooms/{id}/analytics`, and a web `ClassroomAnalyticsView` (mastery distribution, common weak concepts, per-student table).
- **`scripts/smoke_test.py`** — standalone httpx golden-path E2E test against a live stack.
- **5-kid demo seed** — `SEED_DEMO=1` idempotently seeds 5 students spread across mastery buckets, a classroom, a teacher, and a linked parent.
- **`docs/DEMO.md`** — server-hosting and live-demo runbook with a demo-lean env profile.

### Fixed

- **Auth was dead at runtime**: `bcrypt==3.2.2` pin conflicted with the installed `bcrypt` 5.0.0 + `passlib` 1.7.4, crashing `hash_password` on every register/login. Pinned `bcrypt==4.0.1`. (The old "3 pre-existing test failures" were a real runtime bug, not a benign test-env quirk.)
- **`docker/api.Dockerfile`** silently fell back to a hand-written dependency list missing `bcrypt`/`qdrant-client`/`fastembed` whenever the editable install failed (`|| true`). Fixed to install from `pyproject.toml` as the single source of truth (added `[tool.hatch.build.targets.wheel] packages=["src"]`), no silent fallback.
- **Web app could not boot without real Clerk keys**, despite already using a custom JWT for actual authentication. Removed `@clerk/nextjs` usage entirely (`ClerkProvider`, `clerkMiddleware`, `UserButton`, `useUser`, `useAuth`); added `AuthGuard` (client-side route protection) and `AccountButton` (logout).
- **`apiClient.setTokenProvider` was defined but never called** — every web request went out with no `Authorization` header, so all authenticated calls would 401 regardless of the Clerk issue above. Wired to the persisted auth store.
- **Chat SSE chunk encoding was invalid JSON for math content**: manual escaping only handled `"` and `\n`, so backslash sequences like `\frac{1}{2}` produced invalid JSON that the browser silently dropped. Switched to `json.dumps` for every SSE event.
- **`useChat.ts` SSE parsing had no cross-read buffering** — events spanning two network reads failed to parse and were silently lost (garbled/missing streamed text). Added proper line buffering across reads.
- **`docker/web.Dockerfile`** used `pnpm install --frozen-lockfile`, but the repo ships `package-lock.json` (npm), not a pnpm lockfile — the image would never have built. Rewritten for npm; added Next.js `output: 'standalone'` + `outputFileTracingRoot`, and a `.dockerignore`.
- Two pre-existing `tsc` build errors (`UploadDashboard.tsx`, `chat.store.ts`'s unexported `StreamingMessage`) — `tsc --noEmit` is now fully clean.
- `scripts/smoke_test.py` posted to the wrong chat endpoint (`/chat/stream` instead of the real `POST /api/v1/chat`).

### Test / Build Status

213 backend tests passing (0 failing; was 200 passing / 3 failing before the bcrypt fix). `ruff check apps/api/` clean except 31 pre-existing `B008` (FastAPI DI idiom, not a bug). Web `tsc --noEmit` fully clean for the first time.

---

## [0.5.0] — 2026-07-03 — Phase 0.5: Learning Orchestration

**Commit:** `097efbb`  
**Branch:** `master`

### Features Added

#### Backend

**Intent Engine (`intent_engine.py`)**
- New stateless `IntentEngine` service classifying student messages into 7 pedagogical intent categories: `correction_request`, `test_prep`, `clarification`, `problem_solving`, `recall`, `concept_explanation`, `unknown`
- Priority-ordered rule-based matching (zero latency, runs synchronously before LLM call)
- Intent stored on `learning_sessions` (analytics) and injected into LLM system prompt (real-time guidance)

**Concept Memory (`concept_memory_service.py`)**
- New `ConceptMemory` domain entity with `record_interaction()`, `success_rate` property, `needs_different_approach` property
- New `ConceptMemoryModel` DB table (`concept_memory`) with JSONB `teaching_notes` array
- New `AbstractConceptMemoryRepository` ABC + `ConceptMemoryRepository` concrete implementation
- `ConceptMemoryService` with `record_from_extraction()`, `get_all()`, `get_struggling_concepts()`
- Teaching notes capped at 5 per concept; approach derived from Bloom taxonomy level

**LearnerContextService Enhancements**
- New §4 "Teaching History" in system prompt — surfaces up to 3 struggling concepts to LLM with success rates and recurring confusion notes
- Intent-aware §5 adaptation instructions — appends a specific teaching directive for each of 6 recognized intent categories

**Graph Intelligence (`knowledge_graph_service.py`)**
- `get_all_prerequisites(concept_id)` — BFS traversal returning all transitive ancestors in the concept DAG
- `learning_order(concept_ids)` — Kahn's algorithm topological sort on a concept subgraph; handles cycles by appending disconnected nodes

**Learning Path Service (`learning_path_service.py`)**
- `path_to_concept(user_id, target_concept_id)` — ordered list of unmastered prerequisites (capped at 10)
- `get_frontier(user_id)` — concepts the student is ready to learn now (readiness ≥ 50%, not yet mastered ≥ 85%); sorted by readiness, capped at 8
- `curriculum_coverage(user_id)` — per-subject mastery coverage percentage

**Skill Graph Service (`skill_graph_service.py`)**
- Pure derived computation — no DB access
- `BLOOM_TO_SKILLS` mapping: each Bloom level → 2 skill domains
- `build_student_skill_profile()` — derives proficiency per skill domain from mastery records + session Bloom levels
- `top_skills()`, `categorize_bloom_distribution()`

**Route Layer**
- `GET /api/v1/student/memory` — returns all concept teaching memory records
- `GET /api/v1/student/learning-path?target_concept_id=<uuid>` — learning path + frontier + curriculum coverage
- `GET /api/v1/student/skills` — derived skill profile + Bloom distribution
- `intent` field added to `GET /api/v1/student/sessions` response

**Database**
- Migration `006_phase05_orchestration.py`:
  - `intent VARCHAR(30) DEFAULT 'unknown'` added to `learning_sessions`
  - New `concept_memory` table with FK to `users` and `concept_nodes`
  - Index on `concept_memory(user_id)`
  - UniqueConstraint on `(user_id, concept_id)` in `concept_memory`

#### Frontend

**New Components**
- `LearningPathView.tsx` — learning path with prerequisites, coverage bars per subject, frontier "Ready to Learn Now" section with readiness badges
- `SkillsView.tsx` — top skills proficiency bars, Bloom distribution by level, "Needs Reinforcement" card with recurring confusion quotes

**New Pages**
- `app/(dashboard)/student/learning-path/page.tsx`
- `app/(dashboard)/student/skills/page.tsx`

**Updated**
- `Sidebar.tsx` — added Learning Path (`/student/learning-path`) and Skills (`/student/skills`) to nav items with Map and Sparkles icons
- `lib/api/student.ts` — added `ConceptMemory`, `LearningPathNode`, `LearningPath`, `SkillEntry`, `SkillProfile` interfaces; added `getConceptMemory()`, `getLearningPath()`, `getSkillProfile()` API functions; added `intent` field to `LearningSession`

### Bugs Fixed

- **Ruff I001** — import ordering in `dependencies.py` auto-fixed by `ruff check --fix`
- **Ruff F841** — unused `edge_repo` variable removed from `get_learning_orchestrator()`
- **Ruff SIM102** — nested `if any(...): if len(...):` collapsed to `if any(...) and len(...):` in `intent_engine.py`
- **Ruff B008** — `Query(default=None)` in function argument default changed to `Annotated[UUID | None, Query()] = None` in `student.py`

### Tests Added

- `tests/services/test_intent_engine.py` — 10 tests covering all 7 intent categories, case insensitivity, empty string input, long "what is" sentence
- `tests/services/test_skill_graph_service.py` — 8 tests covering BLOOM_TO_SKILLS mapping, profile building with and without sessions, top_skills sorting, Bloom distribution counting
- `tests/services/test_learning_path_service.py` — 8 tests covering frontier computation, mastery/readiness filtering, path generation, curriculum coverage

**Test count: 156 passing, 3 pre-existing failures (bcrypt version conflict — not introduced by this phase)**

---

## [0.4.0] — 2026-06 — Phase 0.4: AI Learning Engine

**Commits:** `8753373`, `085341d`, `022f7d2`

### Features Added
- `ConceptExtractionService` — Groq LLM extracts: primary_concept, bloom_level, misconceptions[], difficulty_level, concepts_discussed[] from each chat exchange
- `MasteryEngine` — per-concept mastery score (0–100) with Bloom-weighted point gains; mastery labels (emerging/developing/mastered)
- `LearningGapDetector` — misconception strings → persistent `learning_gaps` with severity classification (low/medium/high/critical)
- `LearningOrchestrator` — background pipeline combining all learning services; called as FastAPI BackgroundTask
- `KnowledgeGraphService` — concept nodes + prerequisite edges; readiness scoring based on prerequisite mastery
- `NextBestTopicEngine` — recommends next study concepts based on readiness threshold
- `LearnerBehaviorService` — computes behavioral_signals: preferred/struggle Bloom level, response pattern (procedural/conceptual/mixed), engagement streak, complexity trend
- `LearningVelocityService` — mastery points per day, velocity trend (accelerating/steady/decelerating)
- `LearningAnalyticsService` — aggregate analytics: total sessions, mastery counts by label, at-risk concepts, velocity trend
- Frontend: mastery dashboard, gap viewer, knowledge graph, recommendations, statistics, timeline, weak areas views
- Migration 004: concept_nodes, concept_edges, mastery_records, learning_gaps, learning_sessions

### Bugs Fixed (Phase 0.3 overhaul — `022f7d2`)
- Compliance fixes across Phases 0.0–0.4
- Behavioral intelligence enhancements
- Migration 005: `behavioral_signals` JSONB added to `student_profiles`

---

## [0.2.0] — 2026-05 — Phase 0.2: RAG Context Intelligence

**Commits:** `09f6cf1`, `7ab7f08`

### Features Added
- Document ingestion pipeline (PDF, DOCX, PPTX, Markdown, HTML, plain text)
- Token-aware chunking with configurable overlap
- fastembed local embedding generation
- Qdrant vector store integration
- Retrieval service with semantic similarity scoring
- Curriculum-bound RAG: strict filtering blocks off-topic retrievals from entering the LLM context
- `POST /api/v1/rag/query` endpoint
- `GET /api/v1/search` semantic search endpoint
- Redis response cache for RAG (prevents duplicate LLM calls)
- Migrations 002 (knowledge schema), 003 (curriculum RAG)

---

## [0.1.0] — 2026-04 — Phase 0.1: Core Foundation

**Commits:** `4d2d590`, `6ce349e`, `55b4b82`

### Features Added
- FastAPI project scaffold with clean architecture (domain/application/infrastructure/presentation)
- PostgreSQL async ORM (SQLAlchemy 2.0 + asyncpg)
- Alembic migrations infrastructure — migration 001 (users, profiles, settings, conversations, messages)
- JWT authentication (register, login, token refresh)
- Clerk integration (frontend auth, JWT validation in backend)
- Streaming chat endpoint (`POST /api/v1/chat/stream`) with Server-Sent Events
- Groq LLM integration (llama-3.3-70b-versatile)
- Redis rate limiting + response caching
- structlog structured logging
- Prometheus metrics endpoint (`/metrics`)
- CORS configuration
- Request ID middleware
- Next.js 15 frontend with Turbopack
- TanStack Query + Zustand state management
- Radix UI + Tailwind CSS component system
- Chat UI with markdown rendering and syntax highlighting
- Authentication flow (Clerk)
- Docker Compose for local infrastructure (Postgres, Redis, Qdrant)
