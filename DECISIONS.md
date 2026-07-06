# Engineering Decisions — Roognis AI

Records significant design and architecture decisions made during development.

---

## Decision 001 — Clean Architecture with Strict Layer Separation

**Decision:** Use a four-layer clean architecture: domain → application → infrastructure → presentation.

**Reasoning:**
- The learning intelligence logic (mastery scoring, Bloom taxonomy mapping, behavioral analysis) is core business logic that should not be coupled to FastAPI, SQLAlchemy, or Groq specifics.
- Abstract repository interfaces in the domain layer allow test doubles without mocking framework infrastructure.
- Services in the application layer are testable with simple fakes passed as constructor arguments.

**Alternatives considered:**
- Active Record pattern (SQLAlchemy models with embedded business logic) — rejected because it couples domain logic to the ORM and makes unit testing impossible without a database.
- Service-heavy anemic domain — accepted partially (most logic is in services), but key computed properties like `needs_different_approach` and `success_rate` are kept in domain entities.

**Trade-offs:**
- More boilerplate: every new entity needs a domain dataclass, an ORM model, a repository ABC, and a concrete implementation.
- Benefit: the learning engine tests run with no database, no Groq call, no FastAPI — they use constructor-injected fakes.

**Long-term implications:** This architecture allows plugging in alternative LLM providers, vector stores, or databases without changing business logic.

---

## Decision 002 — All Learning Pipeline Work Runs as BackgroundTask

**Decision:** `LearningOrchestrator.process()` is always called as a FastAPI `BackgroundTask`, never awaited in the request path.

**Reasoning:**
- Concept extraction (a Groq LLM call) takes 500ms–2s. Mastery updates, gap detection, and concept memory recording add further async I/O. Putting all this on the critical path would add several seconds to every chat response.
- The student doesn't need to see updated mastery scores on the same response that generated them — they need the AI's answer as fast as possible.

**Alternatives considered:**
- Fire-and-forget with `asyncio.create_task()` — rejected because FastAPI BackgroundTask has proper error handling and lifecycle management.
- Celery worker queue — would add significant infrastructure complexity (broker, worker processes). Overkill for the current scale.

**Trade-offs:**
- Mastery, gaps, and concept memory are always "one message behind" — they update after the response, not before.
- If the background task fails silently (which it does, by design), the student's chat is unaffected but the pipeline record is lost for that session.

**Long-term implications:** If the pipeline needs guaranteed delivery (e.g., billing, compliance), a task queue (Celery, ARQ) should replace BackgroundTask. For now, educational analytics are best-effort.

---

## Decision 003 — Rule-Based Intent Classification (Not LLM-Based)

**Decision:** `IntentEngine.classify()` uses keyword/pattern matching, not an LLM call.

**Reasoning:**
- The intent engine must run before the LLM call to condition the system prompt. An LLM-based classifier would add a full round-trip (500ms–2s) to every chat request's perceived latency.
- For the 7 intent categories, simple pattern matching achieves ~85–90% accuracy on typical student messages. The accuracy trade-off is acceptable because a wrong intent directive rarely produces a noticeably worse response.

**Alternatives considered:**
- A smaller/faster LLM (e.g., llama-3.1-8b-instant via Groq) for intent classification — adds latency and an extra API call; rejected.
- Embedding-based similarity to intent exemplars — more accurate than keywords, still zero-latency, but adds complexity. Could be upgraded later.
- No intent classification — simpler but the LLM cannot distinguish "I'm confused" from "solve this for me."

**Trade-offs:**
- False positives on certain words ("wrong" in "How do I know what's wrong with my answer?" would trigger `correction_request`).
- Zero added cost, zero added latency, fully deterministic and testable.

**Long-term implications:** As the system evolves, the intent engine could be replaced with an embedding-based classifier or a lightweight neural model without changing any downstream code (the API is `classify(question: str) -> str`).

---

## Decision 004 — Skill Profile Is Derived, Not Persisted

**Decision:** `SkillGraphService` computes the student skill profile freshly from mastery records + session data on each API call. No `student_skills` table.

**Reasoning:**
- Skills are an analytical view of existing data, not new independent data. Adding a skills table would require either manual curriculum mapping (unsustainable) or another LLM extraction call (expensive).
- Mastery scores and Bloom levels captured in sessions already encode the cognitive depth of student engagement. The `BLOOM_TO_SKILLS` mapping provides a deterministic transformation.
- A freshly-computed profile is always current. A cached/persisted skill profile could become stale after new mastery updates.

**Alternatives considered:**
- Persist skill scores in a JSONB column on `student_profiles` (alongside `behavioral_signals`) — simpler reads but requires recomputing and updating on every mastery change.
- A separate `student_skills` table with one row per (user, skill) — requires defining the full skill taxonomy in advance, complex migrations when skill taxonomy changes.

**Trade-offs:**
- Recomputed on every `/student/skills` API call — O(n) over mastery records and sessions.
- At current scale (hundreds of records per student) this is negligible. If scale demands, cache the result in Redis with a 5-minute TTL.

**Long-term implications:** When the skill taxonomy grows (psychometric domains, specific academic skills), consider persisting. For now, derived computation keeps the schema simple.

---

## Decision 005 — Single Intent Classification Point in Route Handler

**Decision:** Intent is classified once in the `send_message()` route handler, then passed to both downstream consumers: `ChatService.stream_response()` (before LLM call) and `LearningOrchestrator.process()` (after streaming, as background task).

**Reasoning:**
- Both consumers need the same intent value. If each classified independently, they could get different results (especially if rules change) or we'd pay the classification cost twice.
- The route handler is the only code that owns references to both the streaming closure and the background task — it's the natural single point of control.

**Alternatives considered:**
- Classify in `ChatService.stream_response()` and pass through to background task — would require `stream_response()` to return the intent alongside the stream, complicating the streaming interface.
- Classify in `LearningOrchestrator` only, not in ChatService — would mean the LLM call happens without intent context, defeating the primary purpose.

**Trade-offs:**
- Tight coupling between intent classification and the chat route — if the route splits into microservices later, this coupling must be resolved.
- Benefit: clean, single classification, consistent intent across both uses.

---

## Decision 006 — Concept Memory Uses `get_or_create` Pattern

**Decision:** `ConceptMemoryRepository.get_or_create(user_id, concept_id, concept_name)` either returns an existing record or inserts a new one in a single atomic transaction.

**Reasoning:**
- Every chat session potentially touches concepts that may or may not have a memory record yet. Without `get_or_create`, the service would need a `get` + conditional `create`, adding a round-trip and introducing a race condition under concurrent sessions.

**Alternatives considered:**
- `INSERT ... ON CONFLICT DO UPDATE` (upsert) — cleaner at the DB level but doesn't return the current state of the record. We need the current `times_taught`, `successful_approaches`, etc. to call `record_interaction()` correctly.
- Separate `exists()` check + `create()` — two round-trips + race condition risk.

**Trade-offs:**
- Uses a read + conditional write (SELECT then INSERT) under a transaction — minor overhead vs. upsert. Acceptable for a background task.

---

## Decision 007 — Teaching Notes Capped at 5, Oldest Dropped

**Decision:** `ConceptMemory.record_interaction()` stores teaching notes as `(self.teaching_notes + [note])[-5:]` — always the 5 most recent notes.

**Reasoning:**
- Teaching notes are specific misconception strings from the current session. Older misconceptions are less pedagogically relevant — if a concept was successfully taught 10 sessions ago, the note from that session is noise.
- Unbounded growth of the JSONB field would increase storage and system prompt injection cost over time.

**Alternatives considered:**
- Keep all notes — unbounded growth; old notes reduce signal quality in the system prompt.
- Dedup by content — adds comparison logic; a recurring confusion reappearing is actually signal that it should be surfaced, not deduped.

---

## Decision 008 — `concept_memory_svc` Typed as `Any` in LearnerContextService

**Decision:** In `LearnerContextService.__init__()`, the `concept_memory_svc` parameter is typed as `None` (untyped / implicit `Any`) with a comment `# ConceptMemoryService | None — optional to avoid circular import`.

**Reasoning:**
- `LearnerContextService` and `ConceptMemoryService` are both in `application/services/`. Importing `ConceptMemoryService` in `LearnerContextService` would create an import cycle (both would import from each other indirectly through `domain/repositories/`).
- Python resolves this at runtime — FastAPI's DI injects the correct instance regardless.

**Alternatives considered:**
- Protocol in the domain layer — define `ConceptMemorySvcProtocol` with just the `get_struggling_concepts()` method; both modules can import the Protocol without importing each other. This is the cleanest long-term solution.
- Lazy import inside the method — defers the import until call time, avoiding the module-level cycle. Works but is less readable.

**Long-term implications:** If the service interface needs to evolve (new method signatures), the lack of a type annotation means type errors won't be caught by mypy. Refactor to a Protocol when the interface stabilizes.

---

## Decision 009 — Sequential Numeric Migration Identifiers

**Decision:** Alembic migrations use sequential numeric revision IDs: `001`, `002`, ..., `006`. Each revision explicitly sets `revision = "00N"` and `down_revision = "00(N-1)"`.

**Reasoning:**
- Auto-generated UUIDs from `alembic revision --autogenerate` are hard to order visually and prone to conflicts in a team setting.
- Sequential IDs make it immediately clear which migration came when and catch ordering errors at a glance.

**Alternatives considered:**
- Alembic's default UUID revisions — harder to reason about ordering, especially when cherry-picking.
- Branch-based migrations (multiple heads) — unnecessary complexity for a single-developer project.

**Long-term implications:** Next migration must use revision ID `007`. When creating: `alembic revision --rev-id 007 -m "description"` and manually set `down_revision = "006"`.

---

## Decision 010 — Fail-Open in the Learning Pipeline

**Decision:** The `LearningOrchestrator.process()` method wraps each pipeline stage in a `try/except Exception` block. Failures are logged via structlog but never re-raised.

**Reasoning:**
- The chat response has already been streamed to the student before the background pipeline runs. A pipeline failure cannot be surfaced to the user meaningfully.
- The alternative — propagating exceptions — would cause FastAPI to log an unhandled background task error but still not affect the user's chat experience, while making failures harder to distinguish from "the task didn't run."
- Student-facing learning AI must prioritize availability over data completeness.

**Alternatives considered:**
- Dead letter queue / retry mechanism — appropriate for billing/compliance pipelines; overkill for best-effort educational analytics.
- Fail-closed (raise) — no benefit since the response is already sent; adds confusion.

**Long-term implications:** If session recording becomes critical (e.g., billing based on sessions), the fail-open design must be revisited and at minimum a persistent failure log added.

---

## Decision 011 — Pin `bcrypt==4.0.1` Rather Than `>=4.0.0`

**Decision:** `apps/api/pyproject.toml` pins `bcrypt==4.0.1` exactly, not a range.

**Reasoning:**
- `bcrypt` ≥4.1 (and 5.x) made the 72-byte password-length limit a hard `ValueError` where it was previously a warning; `passlib==1.7.4`'s bcrypt backend was written against the older behavior and cannot initialize against it, crashing `hash_password` on every call.
- `4.0.1` is the newest version that still behaves the old way, and it was verified to fix all 3 previously-failing auth tests (203 → after other work, 213 passing, 0 failing).
- An open range (`>=4.0.0`) would silently reintroduce the exact bug on the next `pip install` once bcrypt 4.1+ is resolved.

**Alternatives considered:**
- Upgrading `passlib` instead — as of this decision, no passlib release fixes bcrypt 5.x compatibility; this wasn't available.
- Switching away from passlib to bcrypt directly — larger surface-area change, rejected under the "only fix defects, don't redesign" constraint in effect at the time.

**Long-term implications:** Revisit this pin when passlib ships bcrypt-5-compatible support; until then, any dependency-update pass must not loosen this pin without re-testing auth.

---

## Decision 012 — Remove Clerk From the Web App Entirely (Not Just Make It Optional)

**Decision:** Deleted all `@clerk/nextjs` usage from `apps/web` (`ClerkProvider`, `clerkMiddleware`, `UserButton`, `useUser`, `useAuth`) rather than gating it behind an environment flag.

**Reasoning:**
- The app's actual authentication has always been a custom JWT (`POST /auth/register`, `POST /auth/login`, `useAuthStore` with Zustand persistence) — Clerk was present in the UI shell but never the real auth path.
- Clerk's `ClerkProvider` and `clerkMiddleware` throw at request time without valid publishable/secret keys, meaning the web app could not boot at all for anyone without a real Clerk account — a hard blocker for local dev and hosting alike.
- A feature flag ("use Clerk if configured, else JWT") would have doubled the auth surface for a component that wasn't doing anything useful.

**Alternatives considered:**
- Provide placeholder/test Clerk keys — rejected; still requires an external account and doesn't remove the maintenance burden of two auth systems.
- Keep Clerk for future social-login and build a real dual-auth path — deferred; not needed for the current MVP/demo scope, revisit if social login becomes a requirement.

**Long-term implications:** `@clerk/nextjs` is still listed in `apps/web/package.json` (unused) to avoid unnecessary lockfile churn in this pass — a future cleanup can remove the dependency outright. If social login is added later, it should integrate with the existing `useAuthStore`/JWT flow rather than reintroducing Clerk as a parallel system.

---

## Decision 013 — Demo Runs With `RETRIEVAL_ENABLED=false` by Default

**Decision:** The 5-kid demo's recommended `.env` sets `RETRIEVAL_ENABLED=false`, turning off RAG/curriculum retrieval for the AI tutor.

**Reasoning:**
- The demo has no curriculum documents loaded into Qdrant; with retrieval on, every query would return "no context found" and route through the same general-answer fallback anyway, but with added latency and an unused Qdrant dependency in the critical path.
- Verified in `chat_service.py` that when RAG returns no context (or is disabled), the service falls back to the `default_system` prompt and answers directly — so disabling retrieval doesn't remove tutor functionality, only removes an unused dependency.
- Matches the user's explicit framing for this demo: "intelligence and the personalization layer takes a back seat" — tangible features (chat, quiz, dashboards) are the priority, not curriculum-grounded RAG accuracy.

**Alternatives considered:**
- Leave retrieval on and accept the latency/complexity cost with an empty vector store — rejected as pointless overhead for this specific demo.
- Upload a small curriculum document set just for the demo — not requested by the user, and adds a step to an already-scoped demo runbook; documented as an option in `docs/DEMO.md` instead of the default.

**Long-term implications:** Any future demo or deployment that wants curriculum-grounded answers must explicitly set `RETRIEVAL_ENABLED=true` and populate Qdrant via the document-upload flow — it will not happen automatically.
