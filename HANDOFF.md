# Development Handoff — Roognis AI

Last updated: 2026-07-03  
Last committed: `097efbb` — Phase 0.5 Learning Orchestration

---

## Current Milestone: Phase 0.5 — Learning Orchestration ✅ COMPLETE

Phase 0.5 added three dimensions of pedagogical intelligence:
1. **Intent classification** — labels every student message before the LLM call
2. **Concept teaching memory** — cross-session record of what teaching approaches worked or failed per concept
3. **Structural learning intelligence** — graph-based learning paths, curriculum coverage, and derived skill profiles

---

## Features Completed

### Phase 0.0 — Infrastructure
- FastAPI scaffold, PostgreSQL + Redis + Qdrant via Docker Compose
- JWT authentication (register/login), Clerk integration placeholder
- Request middleware: logging, rate limiting, request ID injection
- Prometheus metrics endpoint
- Alembic migrations infrastructure

### Phase 0.1 — Core Chat
- Streaming chat endpoint (`POST /api/v1/chat/stream`) with Server-Sent Events
- Conversation + message persistence
- Groq LLM integration (llama-3.3-70b-versatile)
- Basic system prompt with user context
- Frontend: chat UI, auth flow, dashboard shell

### Phase 0.2 — RAG (Context Intelligence)
- Document ingestion pipeline: PDF, DOCX, PPTX, Markdown, HTML
- Chunking (token-aware, configurable overlap)
- Embedding generation (fastembed local / OpenAI configurable)
- Qdrant vector store integration
- Retrieval service with score threshold filtering
- Curriculum-bound RAG: strict academic filtering so off-topic retrievals are blocked
- RAG query endpoint, semantic search endpoint

### Phase 0.3 — Behavioral Intelligence
- `LearnerContextService` — builds structured LLM system prompt from student data
- `LearnerBehaviorService` — computes behavioral signals from session history
- `LearningVelocityService` — mastery points per day, trend detection
- Migration 005 adds `behavioral_signals` JSONB column to `student_profiles`
- System prompt: §1 Identity, §2 Learning Patterns, §3 Knowledge State, §5 Adaptation Instructions

### Phase 0.4 — AI Learning Engine (Backend + Frontend)
- `ConceptExtractionService` — Groq-based extraction: primary concept, Bloom level, misconceptions, difficulty
- `MasteryEngine` — per-concept score with Bloom-weighted gains, interaction count, mastery labels
- `LearningGapDetector` — misconception → learning_gap upsert with severity classification
- `LearningOrchestrator` — background pipeline tying all services together
- `KnowledgeGraphService` — concept graph (nodes + edges), prerequisite queries, readiness scoring
- `NextBestTopicEngine` — recommends next concepts based on readiness + mastery gaps
- `LearningAnalyticsService` — aggregate view: totals, at-risk concepts, velocity trend
- Frontend: mastery dashboard, gap viewer, knowledge graph, recommendations, statistics, timeline
- Migration 004: concept_nodes, concept_edges, mastery_records, learning_gaps, learning_sessions

### Phase 0.5 — Learning Orchestration ✅ (this session)
- `IntentEngine` — 7-category rule-based intent classifier (zero-latency, pre-LLM-call)
- `ConceptMemoryService` — per-concept teaching history: times taught, approach used, success rate, teaching notes
- `ConceptMemory` domain entity + `ConceptMemoryModel` DB table + `AbstractConceptMemoryRepository`
- `ConceptMemoryRepository` — get_or_create, update, list_by_user, get_by_concept
- `KnowledgeGraphService.get_all_prerequisites()` — BFS transitive prerequisite traversal
- `KnowledgeGraphService.learning_order()` — Kahn's topological sort on concept subgraph
- `LearningPathService` — path_to_concept(), get_frontier(), curriculum_coverage()
- `SkillGraphService` — Bloom→skill domain mapping, derived skill profile, Bloom distribution
- `LearnerContextService` §4 Teaching History block — surfaces struggling concepts to LLM
- Intent-aware adaptation instructions in §5 of system prompt
- 3 new API routes: `GET /student/memory`, `GET /student/learning-path`, `GET /student/skills`
- Migration 006: `intent` column on `learning_sessions` + `concept_memory` table
- Frontend: `LearningPathView.tsx`, `SkillsView.tsx`, page files, Sidebar nav items
- 26 new tests (10 intent, 8 skill, 8 learning path) — total 156 passing

---

## Features In Progress

**None.** Phase 0.5 is fully implemented and committed as `097efbb`.

---

## Remaining Roadmap

No formal roadmap exists beyond Phase 0.5. The following are the most logical next phases:

### Phase 0.6 — Psychometric & Adaptive Assessment (suggested)
- Formal quizzing with Item Response Theory (IRT) scoring
- Adaptive difficulty selection based on student ability estimates
- Pre-built question bank seeding from curriculum
- Assessment performance dashboard

### Phase 0.7 — Multi-Persona & Role System (suggested)
- Teacher/parent dashboard with student progress views
- Institution-level admin panel
- Shared knowledge bases per institution

### Phase 0.8 — Production Hardening (suggested)
- Fix bcrypt/passlib version conflict (see Known Bugs)
- End-to-end Playwright tests for critical chat + auth flows
- Production Docker images (multi-stage build)
- CI/CD pipeline (GitHub Actions)
- Proper secret management (no `.env` in production)

---

## Files Modified This Session

### New Files (Phase 0.5)
| File | Purpose |
|------|---------|
| `apps/api/src/application/services/intent_engine.py` | Rule-based intent classifier — 7 categories, pure Python, no I/O |
| `apps/api/src/application/services/concept_memory_service.py` | Per-concept teaching history recorder and query service |
| `apps/api/src/application/services/learning_path_service.py` | BFS-based path generation, frontier detection, curriculum coverage |
| `apps/api/src/application/services/skill_graph_service.py` | Bloom→skill mapping, pure derived computation, no DB |
| `apps/api/src/infrastructure/database/migrations/versions/006_phase05_orchestration.py` | Adds `intent` to `learning_sessions`, creates `concept_memory` table |
| `apps/web/features/student/components/LearningPathView.tsx` | Learning path + frontier + coverage UI component |
| `apps/web/features/student/components/SkillsView.tsx` | Skill profile + Bloom distribution + struggling concepts UI |
| `apps/web/app/(dashboard)/student/learning-path/page.tsx` | Next.js page wrapper for learning path |
| `apps/web/app/(dashboard)/student/skills/page.tsx` | Next.js page wrapper for skills |
| `apps/api/tests/services/test_intent_engine.py` | 10 tests: all 7 intents, case insensitivity, edge cases |
| `apps/api/tests/services/test_skill_graph_service.py` | 8 tests: mapping, profile building, top skills, Bloom distribution |
| `apps/api/tests/services/test_learning_path_service.py` | 8 tests: frontier, path generation, coverage, readiness filtering |

### Modified Files (Phase 0.5)
| File | What Changed |
|------|-------------|
| `apps/api/src/domain/entities/learning.py` | Added `intent` field to `LearningSession`; added full `ConceptMemory` dataclass with `record_interaction()`, `success_rate`, `needs_different_approach` |
| `apps/api/src/infrastructure/database/models/learning.py` | Added `intent` column to `LearningSessionModel`; added `ConceptMemoryModel` |
| `apps/api/src/domain/repositories/learning_repository.py` | Added `AbstractConceptMemoryRepository` ABC |
| `apps/api/src/infrastructure/database/repositories/learning_repository.py` | Added `ConceptMemoryRepository`; updated `_to_session()` and `create()` to handle intent |
| `apps/api/src/application/services/knowledge_graph_service.py` | Added `get_all_prerequisites()` (BFS) and `learning_order()` (Kahn's algorithm) |
| `apps/api/src/application/services/learning_orchestrator.py` | Added `concept_memory_svc` constructor param; added `intent` to `process()`; calls ConceptMemoryService after mastery update |
| `apps/api/src/application/services/learner_context_service.py` | Added `concept_memory_svc` param; `current_intent` param to `build()`; §4 Teaching History block; intent-aware §5 |
| `apps/api/src/application/services/chat_service.py` | Added `current_intent` param to `stream_response()`; passes to LearnerContextService |
| `apps/api/src/application/services/session_memory_service.py` | Added `intent` param to `record()`; passes to `LearningSession` constructor |
| `apps/api/src/application/dtos/learning.py` | Added `intent` to `LearningSessionResponse`; added `ConceptMemoryResponse`, `LearningPathNodeResponse`, `LearningPathResponse`, `SkillEntry`, `SkillProfileResponse` |
| `apps/api/src/application/interfaces/dependencies.py` | Wired `ConceptMemoryService` into ChatService + LearningOrchestrator; added `get_intent_engine()`, `get_concept_memory_service()`, `get_learning_path_service()`, `get_skill_graph_service()` |
| `apps/api/src/presentation/api/v1/chat.py` | Added `IntentEngine` dep; classifies intent synchronously; threads to ChatService and Orchestrator |
| `apps/api/src/presentation/api/v1/student.py` | Added `intent` to session serialization; added 3 new route handlers (`/memory`, `/learning-path`, `/skills`) |
| `apps/web/lib/api/student.ts` | Added `intent` field; added interfaces: `ConceptMemory`, `LearningPathNode`, `LearningPath`, `SkillEntry`, `SkillProfile`; added 3 API functions |
| `apps/web/components/layout/Sidebar.tsx` | Added Map + Sparkles imports; added Learning Path + Skills to `learningNavItems` |

---

## Known Bugs

### Bug 1: bcrypt/passlib version conflict — 3 failing tests
**Severity:** Low (development only — doesn't affect runtime behavior)
**Tests affected:** `test_register_success`, `test_login_success`, `test_login_wrong_password`
**Root cause:** `pyproject.toml` pins `bcrypt==3.2.2` but the test environment has bcrypt 4.x installed. `passlib` 1.7.4 calls `bcrypt.__about__.__version__` which doesn't exist in bcrypt 4.x.
**Fix:** In `pyproject.toml`, change:
```
"bcrypt==3.2.2",
```
to:
```
"bcrypt>=4.0.0",
```
and optionally also update passlib: `"passlib[bcrypt]>=1.7.5"`. Then reinstall.
**Status:** Pre-existing before Phase 0.5. User has not requested a fix.

---

## Known Limitations

1. **Concept memory only records extraction results** — it records `had_misconception=True` when the ConceptExtractionService returns misconceptions, but it cannot detect when the LLM simply gave a bad explanation without a follow-up student question. Teaching success/failure is approximate.

2. **Skill profile accuracy degrades without session data** — if a student has mastery records but no learning sessions (e.g., data imported from an external system), the fallback score-based Bloom estimation is coarse.

3. **Learning path capped at 10 nodes** — `path_to_concept()` returns at most 10 prerequisite nodes. Long prerequisite chains to advanced concepts are truncated. No UI indicator is shown when this cap is hit.

4. **Frontier capped at 8** — `get_frontier()` returns at most 8 concepts. Students in subjects with many ready-to-learn concepts see only the 8 most ready.

5. **Intent engine is keyword-only** — no semantic understanding. "My answer might be wrong" could misclassify as `correction_request` (contains "wrong"). These misfires are harmless but imperfect.

6. **Knowledge graph must be seeded manually** — the `concept_nodes` and `concept_edges` tables must be pre-populated (via scripts or admin API) for the learning path and frontier features to work. No auto-seeding from curriculum.

7. **No real-time profile update** — the student profile's `behavioral_signals` column is updated after every session in the background, but the frontend doesn't subscribe to changes. The profile page must be refreshed to see updated signals.

---

## Technical Debt

1. **`pyproject.toml` pins bcrypt==3.2.2** — conflicts with bcrypt 4.x. Fix by upgrading to `>=4.0.0`.

2. **`concept_memory_svc` typed as `Any`** — in `LearnerContextService.__init__()` to avoid circular imports. A cleaner solution would be to introduce a Protocol/interface in the domain layer that both services can reference.

3. **`learning_order()` uses `list.pop(0)`** — O(n) operation. For large concept graphs, should use `collections.deque` with `popleft()` for O(1). Not a concern at current scale.

4. **No pagination on `/student/memory`** — returns all concept memory records for a user. Could be large for students who have studied many concepts.

5. **`get_skill_profile()` route fetches last 50 sessions** — hardcoded `limit=50`. Should be configurable or load more for accurate Bloom distribution.

6. **No concept graph seeding in development** — the `scripts/seed.py` likely doesn't seed concept_nodes/edges. New developers need to manually populate the graph to test learning path features.

---

## Pending Refactors

- None required. The codebase is clean after Phase 0.5 Ruff fixes.

---

## Current Blockers

- None. Phase 0.5 is committed and passing (156 tests, 3 pre-existing failures).

---

## Assumptions Made

1. The `concept_nodes` and `concept_edges` tables are pre-populated with actual curriculum data. If they are empty, learning path and frontier features return empty results gracefully.

2. Groq API key is valid and the models `llama-3.3-70b-versatile` and `llama-3.1-8b-instant` are accessible.

3. The Bloom level extracted by `ConceptExtractionService` is accurate enough to derive pedagogical intent (approach = "conceptual" if Bloom rank ≥ 3). The LLM extracts these from the question/response content.

4. A "successful teaching interaction" is one where the student's next question shows no misconceptions on the same concept. This is a proxy — not a direct measure of learning.

---

## Recommended Next Development Tasks

In priority order:

1. **Seed curriculum knowledge graph** — populate `concept_nodes` and `concept_edges` with real CBSE/NCERT curriculum data for at least 2 subjects and 2 grades. This unlocks LearningPath and Frontier features for real testing.

2. **Fix bcrypt/passlib version conflict** — update `pyproject.toml` to use `bcrypt>=4.0.0`. Eliminates 3 test failures and removes a potential runtime risk on fresh installs.

3. **Add concept graph seeding to `scripts/seed.py`** — so new developers can run a single script to get a usable development environment.

4. **Phase 0.6 design** — decide the next major feature area (adaptive assessment, teacher dashboard, multi-persona, or production hardening).

---

## Context That Exists Only In This Conversation

- The Phase 0.5 implementation was done after a context-compacted session. The previous session committed `022f7d2` (Phase 0.3 overhaul), `085341d` (Phase 0.4 frontend), and `8753373` (Phase 0.4 backend). Phase 0.5 is commit `097efbb`.

- The user's standing constraint is: "Do not redesign existing modules. Build on top of the current implementation. Maintain compatibility with the existing architecture. Ensure every new component is modular, scalable, and extensible for future psychometric, adaptive learning, and multi-persona systems."

- The Ruff linting issues fixed in Phase 0.5: I001 (import ordering auto-fixed), F841 (unused `edge_repo` variable), SIM102 (nested if → and), B008 (Query() in argument default → Annotated[..., Query()] = None).

- The "Roognis_Ai_Backend_repo" directory in the project root is untracked (shows in git status). Do not add or commit it without the user's instruction.
