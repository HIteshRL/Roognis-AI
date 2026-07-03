# Roognis AI — Chronological Roadmap (Phase 0.0 → v0.71)

A complete history of platform iterations, capabilities added, and architectural dependencies.

---

## Phase 0.0 — Foundation & Auth (Base Layer)

**Completed:** [Git commit 219ee35](https://github.com/roognis/roognis-ai/commit/219ee35)

**What it delivers:**
- User registration/login (Clerk identity + local PostgreSQL sync)
- JWT token-based request auth
- Rate limiting (Redis)
- Standard API response envelope (success/data/message/request_id)
- Database: users, profiles, settings tables
- SSE streaming infrastructure (no websockets)

**Key Files:**
- `apps/api/src/presentation/api/v1/auth.py` — register, login routes
- `apps/api/src/application/services/auth_service.py` — user mgmt
- `apps/api/src/infrastructure/database/models/` — users, profiles
- `apps/web/app/(auth)/` — signup/login pages

**Frontend Stack:**
- Clerk SDK (`@clerk/nextjs`)
- Next.js 15.1.3, TypeScript, Tailwind CSS
- Zustand for state

**Backend Stack:**
- FastAPI 0.115.6, Python 3.12
- PostgreSQL 16 (asyncpg)
- Redis 7 (rate limiting)
- SQLAlchemy 2.0 async ORM

**Dependencies:** None (base layer)

**Config Keys:** `DATABASE_URL`, `REDIS_URL`, `API_SECRET_KEY`, `CLERK_SECRET_KEY`, `CLERK_PUBLISHABLE_KEY`

---

## Phase 0.1 — Chat & Streaming (Core Feature)

**Completed:** Same as Phase 0.0

**What it delivers:**
- Real-time chat interface (SSE streaming)
- Conversation history
- Message persistence
- User-owned conversation isolation

**Key Files:**
- `apps/api/src/presentation/api/v1/chat.py` — POST /chat/stream, GET /chat/history
- `apps/api/src/application/services/chat_service.py` — orchestrates LLM + persistence
- `apps/web/features/chat/` — ChatCanvas, MessageBubble, ChatInput
- `apps/web/features/chat/hooks/useChat.ts` — SSE stream handling

**Database Tables Added:**
- `conversations` (user_id, title, subject, chapter, created_at)
- `messages` (conversation_id, role, content, created_at)

**SSE Event Format:**
```
data: {"type":"chunk","content":"..."}
data: {"type":"meta","sources":[...],"intent":"..."}
data: {"type":"done"}
```

**Dependencies:**
- ✅ Phase 0.0 (auth, rate limiting)

**Config Keys:** `GROQ_API_KEY`, `GROQ_CHAT_MODEL` (default: `llama-3.3-70b-versatile`)

---

## Phase 0.2 — RAG & Knowledge Base (Semantic Search)

**Completed:** [Migration 002](apps/api/src/infrastructure/database/migrations/versions/002_knowledge.py)

**What it delivers:**
- Document upload / ingestion pipeline (async chunking + embedding)
- Vector store (Qdrant)
- Semantic search against uploaded documents
- RAG context injected into LLM prompts

**Key Files:**
- `apps/api/src/application/services/knowledge_library_service.py` — upload/delete docs
- `apps/api/src/application/services/ingestion_pipeline.py` — async chunking + embedding
- `apps/api/src/application/services/retrieval_service.py` — semantic search
- `apps/api/src/application/services/rag_service.py` — injects sources into system prompt
- `apps/api/src/infrastructure/database/models/knowledge.py` — documents, chunks, ingestion_jobs
- `apps/web/features/upload/` — document upload UI

**Database Tables Added:**
- `knowledge_bases` (name, subject, grade)
- `documents` (kb_id, filename, status, chunk_count)
- `chunks` (doc_id, content, embedding_id)
- `ingestion_jobs` (status tracking: queued|running|completed|failed)

**Vector DB:** Qdrant (local or cloud)

**Embedding Provider Abstraction:**
- `infrastructure/embeddings/base.py` — `AbstractEmbeddingProvider`
- `infrastructure/embeddings/fastembed_provider.py` — local (default)
- `infrastructure/embeddings/openai_provider.py` — cloud alternative
- `infrastructure/embeddings/factory.py` — provider selection by config

**LLM Integration:** RAG context passed to `PromptAssemblyService`, which builds the system prompt with top-k sources.

**Dependencies:**
- ✅ Phase 0.0 (auth)
- ✅ Phase 0.1 (chat, SSE)

**Config Keys:** `QDRANT_URL`, `QDRANT_API_KEY`, `EMBEDDINGS_PROVIDER` (fastembed|openai), `OPENAI_EMBEDDING_MODEL`

---

## Phase 0.3 — Curriculum & Knowledge Graph (Learning Structure)

**Completed:** [Migration 003](apps/api/src/infrastructure/database/migrations/versions/003_curriculum.py)

**What it delivers:**
- Curriculum schema (concepts, prerequisites, relationships)
- Knowledge graph visualization
- Concept-level mastery tracking
- Concept extraction from student questions
- Bloom's taxonomy integration (difficulty/cognitive level)

**Key Files:**
- `apps/api/src/application/services/concept_extraction_service.py` — extracts concepts from questions (Groq `llama-3.1-8b-instant`)
- `apps/api/src/application/services/knowledge_graph_service.py` — builds/queries graph
- `apps/api/src/infrastructure/database/models/learning.py` — concept_nodes, concept_edges, mastery_records
- `apps/web/features/student/knowledge-graph/` — graph visualization (D3.js or Cytoscape)

**Database Tables Added:**
- `concept_nodes` (name, subject, chapter, bloom_level, difficulty, grade)
- `concept_edges` (source_id, target_id, relationship_type: prerequisite|related|extends)
- `mastery_records` (user_id, concept_id, score 0–100, interaction_count, last_updated)
- `learning_sessions` (user_id, conversation_id, subject, chapter, grade, question, primary_concept, concepts_discussed, bloom_level, difficulty_level, misconceptions, token_count, duration_ms)

**Concept Extraction Prompt:** Groq determines primary_concept + related concepts + Bloom's level from student question.

**Graph Algorithms:**
- Kahn's algorithm for topological sort (learning order)
- DFS for finding prerequisites

**Dependencies:**
- ✅ Phase 0.0 (auth)
- ✅ Phase 0.1 (chat, sessions)
- ✅ Phase 0.2 (RAG foundation)

**Config Keys:** `GROQ_EXTRACTION_MODEL` (default: `llama-3.1-8b-instant`)

---

## Phase 0.4 — Learning Engine & Analytics (Personalization)

**Completed:** [Migration 004](apps/api/src/infrastructure/database/migrations/versions/004_learning_engine.py)

**What it delivers:**
- Per-student mastery profiles
- Learning velocity (pace tracking)
- Gap detection (misconceptions)
- Weak area recommendations (NextBestTopic)
- Learning analytics dashboard

**Key Files:**
- `apps/api/src/application/services/mastery_engine.py` — updates concept scores post-answer
- `apps/api/src/application/services/learning_gap_detector.py` — finds misconceptions
- `apps/api/src/application/services/next_best_topic_engine.py` — recommends next topics
- `apps/api/src/application/services/learning_velocity_service.py` — confidence/progress tracking
- `apps/api/src/application/services/learning_analytics_service.py` — dashboard summaries
- `apps/web/features/student/mastery/` — mastery heatmap
- `apps/web/features/student/gaps/` — misconception list + resolve action
- `apps/web/features/student/statistics/` — analytics dashboard

**Database Tables Added:**
- `learning_gaps` (user_id, concept_id, severity, reason, confidence, occurrence_count, is_resolved)

**Algorithms:**
- Confidence scoring: interaction_count + success_rate → mastery 0–100
- Velocity: derivative of mastery over time
- Gap detection: low mastery + recent errors → gap

**API Endpoints Added:**
- `GET /student/mastery` — mastery for all concepts
- `GET /student/gaps` — current misconceptions
- `POST /student/gaps/{id}/resolve` — mark resolved
- `GET /student/recommendations` — NextBestTopic
- `GET /student/analytics` — summary stats

**Learning Path (v0.4 only):** Topological sort of unmastered prerequisites.

**Dependencies:**
- ✅ Phase 0.0 (auth)
- ✅ Phase 0.1 (chat, sessions)
- ✅ Phase 0.3 (curriculum, concepts)

**Config Keys:** None new

---

## Phase 0.5 — Behavioral Intelligence & Memory (Adaptive Teaching)

**Completed:** [Migration 006](apps/api/src/infrastructure/database/migrations/versions/006_phase_05.py) (skipped 005 for versioning)

**What it delivers:**
- Intent classification (why is the student asking?)
- Teaching history per concept (what explanations have been tried)
- Behavioral signals (engagement, learning style, dominant subject)
- Skill profile (derived from mastery + sessions, not persisted)
- Adaptive system prompt (student context injected pre-response)
- Learning path calculation (frontier + coverage)

**Key Files:**
- `apps/api/src/application/services/intent_engine.py` — stateless rule-based classify (question|stuck|curious|verify|distraction)
- `apps/api/src/application/services/concept_memory_service.py` — persistent teaching history
- `apps/api/src/application/services/learner_behavior_service.py` — signals (engagement_streak, response_pattern, dominant_subject, strengths)
- `apps/api/src/application/services/skill_graph_service.py` — derives skills (never persisted)
- `apps/api/src/application/services/learning_path_service.py` — frontier + coverage
- `apps/api/src/application/services/learner_context_service.py` — assembles system prompt context
- `apps/api/src/application/services/learning_orchestrator.py` — post-response pipeline (extraction + analysis)
- `apps/web/features/student/learning-path/` — visual learner journey
- `apps/web/features/student/skills/` — skill profile

**Database Tables Added:**
- `concept_memory` (user_id, concept_id, times_taught, successful_approaches, failed_approaches, last_approach, teaching_notes JSONB, last_taught)
- `student_profiles.behavioral_signals` — JSONB: {engagement_streak, response_pattern, dominant_subject, strengths[], dominant_time_of_day}

**Modified Tables:**
- `learning_sessions` — added `intent` column (default "unknown"), server_default for backcompat

**Behavioral Signals Schema:**
```json
{
  "engagement_streak": 5,
  "response_pattern": "visual|kinesthetic|analytical|mixed",
  "dominant_subject": "Physics",
  "strengths": ["Algebra", "Calculus"],
  "dominant_time_of_day": "evening",
  "session_count": 42,
  "total_duration_minutes": 320
}
```

**Intent Classification (Rule-Based, Zero Latency):**
- "question" — asks for explanation
- "stuck" — expresses confusion/difficulty
- "curious" — explores beyond curriculum
- "verify" — checks correctness
- "distraction" — off-topic / non-academic

**Teaching Memory Approach:**
- Stores `successful_approaches` + `failed_approaches` (keywords/strategies)
- `teaching_notes[-5:]` cap (last 5 only)
- Capped at 5 weak concepts in system prompt to avoid token explosion

**Skill Profile (Computed, Not Stored):**
- Derives from mastery_records + learning_sessions
- `SkillGraphService.get_skill_profile(user_id)` → fresh calculation
- No `skills` table needed

**Learning Path Calculation:**
- `frontier` — concepts ready to learn (prerequisites met, not mastered)
- `coverage` — % of curriculum mastered
- Kahn's algorithm with fail-open (unprocessed nodes appended)

**API Endpoints Added:**
- `GET /student/memory` — teaching history + effective strategies
- `GET /student/learning-path` — frontier, coverage, next steps
- `GET /student/skills` — derived skill profile

**LearnerContextService Integration:**
- Caps weak concepts, active gaps, strengths in system prompt
- Injects behavioral signals + teaching history
- Fail-open: if service fails, response still streams

**Learning Orchestrator (Post-Response Pipeline):**
- Runs as `BackgroundTask` (zero added latency)
- Steps: concept extraction → mastery update → gap detection → memory record → behavior analysis
- All steps wrapped in try/except (fail-open per step)

**Dependencies:**
- ✅ Phase 0.0 (auth)
- ✅ Phase 0.1 (chat, sessions)
- ✅ Phase 0.2 (RAG)
- ✅ Phase 0.3 (curriculum, concepts)
- ✅ Phase 0.4 (learning engine, mastery)

**Config Keys:** `MAX_WEAK_CONCEPTS`, `MAX_ACTIVE_GAPS`, `MAX_TEACHING_NOTES` (all with defaults)

---

## Phase 0.7 — Vision & Attachments (Image Understanding)

**Completed:** [Migration 009](apps/api/src/infrastructure/database/migrations/versions/009_attachments.py)

**What it delivers:**
- Image upload from student (diagrams, screenshots, photos)
- Vision model integration (Groq `llama-2-90b-vision-preview`)
- Image understanding injected into chat context
- Attachment persistence + serving

**Key Files:**
- `apps/api/src/application/services/attachment_service.py` — upload, validate, serve
- `apps/api/src/application/services/vision_analyzer_service.py` — Groq vision call
- `apps/api/src/infrastructure/database/models/attachment.py` — MessageAttachmentModel
- `apps/api/src/presentation/api/v1/chat.py` — `POST /upload`, `GET /attachments/{id}`
- `apps/web/features/chat/components/AttachmentImage.tsx` — image preview
- `apps/web/features/chat/components/UploadArea.tsx` — drag-drop upload

**Database Tables Added:**
- `message_attachments` (id, user_id, message_id, storage_path, content_type, file_size, kind, created_at)

**Attachment Schema:**
- `kind`: "image" (Phase 0.7), "video" (v0.71)
- `content_type`: "image/png", "image/jpeg", "video/mp4"
- `storage_path`: local filesystem path (configurable `storage_local_path`)
- Served authenticated via JWT

**Vision Integration:**
- Vision model called if image is uploaded before student message
- Vision context prepended to user message: "I've attached an image: [vision analysis]"
- Enables teacher to understand student's visual confusion

**File Size Limits:**
- Default 8 MB per image
- Configurable via `max_image_size_bytes`

**Local Storage:**
- `LocalFileStorage` in `infrastructure/storage/local_storage.py`
- Saves to `{storage_local_path}/chat/{user_id}/{attachment_id}.{ext}`
- Docker mount: `/uploads`

**Dependencies:**
- ✅ Phase 0.0 (auth)
- ✅ Phase 0.1 (chat)
- ✅ Phase 0.3 (concepts)
- ✅ Phase 0.5 (learning orchestrator)

**Config Keys:** `STORAGE_LOCAL_PATH`, `ALLOWED_IMAGE_TYPES`, `MAX_IMAGE_SIZE_BYTES`, `GROQ_VISION_MODEL`

---

## v0.71 — Generative Multimodal (Image + Video Generation)

**Completed:** All layers verified (migrations, tests, TypeScript compile, server compile)

**What it delivers:**
- **Default generated images** on every tutor answer (Fal Flux/SDXL, hosted)
- **On-demand video generation** when student doesn't understand (LTX-Video, self-hosted GPU)
- **3-pane Classroom/NotebookLM layout** (Subject→Chapter rail, chat canvas, context panel)
- Media job async system with progress polling
- Enhanced psychographic context in chat

**Key Files:**

**Backend — Image Generation:**
- `apps/api/src/infrastructure/imagegen/` — provider abstraction (Fal + stub)
  - `base.py` — `AbstractImageGenerator.generate(prompt, size) → ImageResult`
  - `fal_provider.py` — calls Fal API (`fal-ai/flux/schnell`), polls, downloads bytes
  - `stub_provider.py` — returns minimal PNG for dev without API key
  - `factory.py` — `get_image_generator()` by `image_gen_provider` (fal|stub)
- `apps/api/src/application/services/response_image_service.py`
  - `build_prompt(question, concept, subject, chapter)` → education-safe prompt (500 chars)
  - `generate(prompt)` → call provider, fail-open on error
  - `persist(user_id, message_id, result)` → store in `message_attachments`, return attachment
- `apps/api/src/application/services/chat_service.py` — integration
  - Create image_task at stream start (concurrent with text)
  - Await after message persists
  - Emit SSE `image` event before `done`

**Backend — Video Generation:**
- `apps/api/src/infrastructure/videogen/` — provider abstraction (LTX + stub)
  - `base.py` — `AbstractVideoGenerator.generate(prompt, num_frames, fps) → VideoResult`
  - `ltx_provider.py` — LTX-Video pipeline (lazy torch/diffusers, CUDA, module-cached)
  - `stub_provider.py` — imageio placeholder or "GPU unavailable" message
  - `factory.py` — `get_video_generator()` by `video_gen_provider` (ltx|stub)
- `apps/api/src/application/services/video_generation_service.py`
  - `request(user_id, message_id) → MediaJob(queued)` — verify ownership, build prompt
  - `run(job_id)` — BackgroundTask, opens own AsyncSessionLocal, runs in thread executor under GPU semaphore, persists mp4 + attachment, updates status
  - Own session pattern mirrors `IngestionPipeline.run`
- `apps/api/src/infrastructure/database/models/media_job.py` — SQLAlchemy ORM
- `apps/api/src/domain/repositories/media_job_repository.py` — abstract + concrete
- **Migration 010:** `media_jobs` table (user_id FK CASCADE, message_id FK CASCADE, kind, status, prompt, attachment_id, progress, error_message)

**Backend — Routes:**
- `POST /chat/messages/{id}/video` (202 Accepted) → request + queue
- `GET /chat/media-jobs/{id}` → poll status/progress/url
- `GET /chat/subjects/{subject}/chapters` → chapters for left rail
- `GET /chat/history?chapter=...` → chapter filter (new optional param)
- Video served by **existing** `GET /chat/attachments/{id}` (no new endpoint)

**Backend — Config:**
- Image: `image_gen_enabled`, `response_image_enabled`, `image_gen_provider` (fal|stub), `fal_api_key`, `image_gen_model`, `image_gen_size`
- Video: `video_gen_enabled`, `video_gen_provider` (ltx|stub), `ltx_model_id`, `video_num_frames`, `video_fps`, `max_concurrent_video_jobs`

**Backend — Dependencies:**
- `pyproject.toml` — new optional `[video]` extra (torch, diffusers, transformers, accelerate, imageio, sentencepiece)
  - Install: `pip install -e '.[video]'` on CUDA box; omit on dev machines without GPU

**Frontend — Layout & Navigation:**
- `features/chat/components/ClassroomChatView.tsx` — 3-pane shell (Subject→Chapter rail, chat, context)
- `SubjectChapterRail.tsx` — left sidebar: Classroom-style subject cards → chapters → past conversations ("Inferences")
- `ContextPanel.tsx` — right sidebar: RAG sources + psychographic snapshot (mastery, streak, learning style, strengths)
- Repointed `app/(dashboard)/chat/page.tsx` + `[id]/page.tsx` to `ClassroomChatView`

**Frontend — Image & Video UI:**
- `VideoAttachment.tsx` — authenticated `<video>` blob player
- `VideoJobCard.tsx` — progress bar while job runs
- `MessageVideoControl.tsx` — "I don't understand — show me a video" button + job orchestration
- `MessageBubble.tsx` enhanced:
  - Renders existing generated images (`kind="image"`)
  - Renders existing videos (`kind="video"`)
  - Shows video control if no video yet
- `useVideoJob.ts` hook — request video, poll until terminal, return job
- `useChat.ts` updated — handle SSE `image` event, set `streamingImageId` for live preview
- `chat.store.ts` — added `streamingImageId` state + setter

**Frontend — API & Types:**
- `lib/api/chat.ts` — `getChapters(subject)`, `requestVideo(messageId)`, `getMediaJob(jobId)`
- `lib/api/client.ts` — `fetchAttachmentUrl(id)` for authenticated blob serving
- `packages/shared/src/dtos/index.ts` — `MediaJobDto`, `ChapterDto`

**Database Tables Added:**
- `media_jobs` (id UUID PK, user_id FK, conversation_id, message_id FK, kind, status, prompt, attachment_id FK, progress, error_message, timestamps)

**Message Attachments Reuse:**
- Phase 0.7 `message_attachments` table already supports:
  - `kind`: now "image" (generated) or "video" (generated), was only used for Phase 0.7 uploads
  - `content_type`: "image/png", "image/jpeg", "video/mp4"
  - No schema changes needed

**SSE Events:**
- Existing: `chunk` (text), `meta` (RAG sources + intent), `done`
- **New:** `image` event before `done`:
  ```json
  {"type":"image","attachment_id":"uuid","url":"/api/v1/chat/attachments/uuid"}
  ```

**Job Status Lifecycle:**
```
queued → running → completed (+ attachment_id)
      ↘          ↗
         failed (+ error_message)
```

**GPU Semaphore (In-Process):**
- Process-level `asyncio.Semaphore(max_concurrent_video_jobs)` (default 1)
- Prevents OOM from multiple parallel torch/diffusers models
- Future: move to dedicated worker queue

**Known Limitations:**
- Video runs in-process (no worker queue yet)
- Attachment serving has no HTTP range/seeking (OK for short clips)
- Default image adds ~1–3s (overlapped) + Fal cost
- Toggle default image via `response_image_enabled`

**Dependencies:**
- ✅ All prior phases (0.0–0.5, 0.7)
- Reuses Phase 0.7 `message_attachments` + `AttachmentService`

**Config Keys:** Image + video keys (see above)

---

## Dependency Graph

```
Phase 0.0 (Auth)
    ↓
Phase 0.1 (Chat & Streaming)
    ↓ ├─→ Phase 0.2 (RAG & Knowledge Base)
    ↓ │       ↓
    ↓ └─→ Phase 0.3 (Curriculum & Knowledge Graph)
    ↓           ↓
    └─→ Phase 0.4 (Learning Engine & Analytics)
            ↓
        Phase 0.5 (Behavioral Intelligence & Memory)
            ↓
        Phase 0.7 (Vision & Attachments)
            ↓
        v0.71 (Generative Multimodal + 3-Pane Layout)
```

---

## Feature Roadmap (Proposed Future)

**Out of scope for this summary, but documented in individual phase files:**
- Dedicated video job queue (Bull, Celery, or similar)
- HTTP range requests for video seeking
- Per-student media quotas
- Audio narration / text-to-speech
- Quiz generation & adaptive testing
- Parent/teacher dashboards
- Offline mode

---

## Verification Checklist

All phases follow:
- ✅ Ruff lint (no comments unless WHY is non-obvious, no design docs)
- ✅ Type safety (Python 3.12, TypeScript strict)
- ✅ Database migrations (sequential numeric, never autogenerate)
- ✅ Clean Architecture (domain → application → infrastructure → presentation)
- ✅ Fail-open learning pipeline (individual step failures don't block response)
- ✅ Dependency injection (all services wired in `dependencies.py`)
- ✅ Async I/O (all DB/API calls are async)
- ✅ Test coverage (at minimum: happy path + edge cases for new services)

---

## Current Deployment State

**Production Ready:** Phase 0.0–0.7 (images understood, chat works, learning analytics active)

**v0.71 Status:** Code complete, verified (181 tests pass, TypeScript clean, dev server compiles, ruff clean).

**To Deploy v0.71:**
1. `alembic upgrade head` (applies migrations 001–010)
2. Set `FAL_API_KEY` (or `IMAGE_GEN_PROVIDER=stub` for dev)
3. Optional: `pip install -e '.[video]'` + set `VIDEO_GEN_PROVIDER=ltx` on CUDA machine (or `stub` elsewhere)
4. Redeploy API + web

---

## Documentation References

- **CLAUDE.md** (root) — core operating manual, tech stack, coding standards, database schema, design principles
- **docs/ARCHITECTURE.md** (proposed) — system diagram, service interactions, data flow
- **Commit messages** — per-phase implementation details (git log --oneline)
- **Phase-specific READMEs** (proposed) — each phase folder
- **tests/** — behavior specification by example

