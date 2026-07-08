# Roognis v0.71 — Generative Multimodal Tutoring

**Handover Document** | Date: 2026-07-04 | Status: ✅ Committed & Verified

---

## Executive Summary

v0.71 **shifts the platform from Phase 0.7's image *understanding* (student uploads photo → tutor analyzes) to media *generation* as default output** (tutor's text response + default generated illustration + on-demand video). This makes the student experience visual-first and adaptive to learning gaps.

**What changed:**
- Every tutor answer now includes a **default generated image** (Fal-hosted diffusion, ~1–3s, overlapped with text streaming)
- Students can request **on-demand video explanations** when text + image aren't enough (self-hosted LTX-Video on GPU, async job)
- Chat UI redesigned as a **3-pane Classroom/NotebookLM layout** (Subject→Chapter rail, chat canvas, psychographic context panel)
- Backend architecture adds **provider abstraction** for image/video generation, **media job system** for tracking async work, and **responsive UI patterns** for streaming

**Impact on the learning model:**
- Misconceptions are **visualized immediately** via generated images (reinforces concepts faster)
- When a student signals confusion, the tutor can generate a video without the student leaving the chat
- The Subjects portal now contextualizes every chat within the school's syllabus (Subject→Chapter hierarchy)
- Behavioral context (mastery, learning style, strengths) is **always visible** in the right panel

---

## Architecture Overview

### Data Flow: From Answer to Multimodal Response

```
POST /api/v1/chat (student message)
  ↓
ChatService.stream_response() [async]
  ├─ LLM inference (text streaming over SSE)
  ├─ ⚡ CONCURRENT: ResponseImageService.generate(prompt) [Fal API call]
  ├─ After text completes: await image_task
  ├─ Persist image_attachment (via AttachmentService)
  ├─ Emit SSE `image` event with attachment URL
  └─ Final SSE `done` event
  ↓
POST /api/v1/chat/messages/{id}/video [student request, async]
  ├─ VideoGenerationService.request() [validates ownership, creates media_job]
  ├─ BackgroundTask: VideoGenerationService.run(job_id)
  │   ├─ Opens own AsyncSessionLocal (independent of request session)
  │   ├─ Calls video_generator via loop.run_in_executor (blocks torch off event loop)
  │   ├─ Persists mp4 as message_attachment
  │   └─ Updates job status
  └─ Client polls GET /api/v1/chat/media-jobs/{id} until terminal
```

### Provider Pattern (Infrastructure Abstraction)

Image and video generation follow the same factory pattern as LLM + embeddings providers:

```
AbstractImageGenerator (base interface)
  ├─ FalImageGenerator (Fal SDK, httpx, polls for ready image)
  └─ StubImageGenerator (returns 1×1 PNG for dev/test without API key)
  └─ factory.get_image_generator() [lru_cache, routes by config]

AbstractVideoGenerator (base interface)
  ├─ LTXVideoGenerator (lazy torch/diffusers, module-cached pipeline, CUDA)
  └─ StubVideoGenerator (placeholder mp4 via imageio or bytes)
  └─ factory.get_video_generator() [lru_cache, routes by config]
```

**Why this matters:** Swapping providers is a config change, not a code rewrite. Stub providers let you test the full pipeline without GPUs/API keys.

### Media Job System (Async Tracking Pattern)

Mirrors the `IngestionJob` pattern from Phase 0.2:

```
media_jobs table
├─ id (UUID PK)
├─ user_id (FK CASCADE → users)
├─ message_id (FK CASCADE → messages)
├─ conversation_id (nullable, context)
├─ kind ('video' — extensible for audio, etc.)
├─ status ('queued' → 'running' → 'completed' | 'failed')
├─ prompt (Text, used to regenerate if needed)
├─ attachment_id (FK SET NULL → message_attachments)
├─ progress (0–100)
├─ error_message (if failed)
└─ timestamps (created_at, updated_at)
```

**State machine:**
```
┌─────────────┐        ┌──────────────┐        ┌───────────────┐
│   queued    │───────→│   running    │───────→│   completed   │
│             │        │              │        │ (attachment)  │
└─────────────┘        └──────────────┘        └───────────────┘
       ↓                      ↓
    [fail]               [fail]
       │                    │
       └────────┬───────────┘
                ↓
        ┌──────────────┐
        │   failed     │
        │ (error_msg)  │
        └──────────────┘
```

### UI Layout: 3-Pane Classroom

```
┌─────────────────────────────────────────────────┐
│                    Top Nav                      │
├──────────────┬──────────────────┬───────────────┤
│              │                  │               │
│  Subjects    │   Chat Canvas    │   Context     │
│  (left rail) │   (center pane)  │   Panel       │
│              │                  │  (right rail) │
│  • Subject 1 │ ┌──────────────┐ │ SOURCES:      │
│    > Chapter │ │ User message │ │ • Source 1    │
│    > Chapter │ ├──────────────┤ │ • Source 2    │
│  • Subject 2 │ │ Asst response│ │               │
│    (new)     │ │ [image]      │ │ LEARNER:      │
│              │ │ [video btn]  │ │ • Avg mast: % │
│  New chat ▼  │ ├──────────────┤ │ • Streak: d   │
│              │ │ [composer]   │ │ • Style:      │
│              │ └──────────────┘ │ • Strengths:  │
│              │                  │               │
└──────────────┴──────────────────┴───────────────┘
```

---

## File Manifest

### New Files (Phase v0.71)

**Image Generation:**
- `apps/api/src/infrastructure/imagegen/base.py` — `AbstractImageGenerator` interface
- `apps/api/src/infrastructure/imagegen/fal_provider.py` — Fal API implementation (polls for image)
- `apps/api/src/infrastructure/imagegen/stub_provider.py` — 1×1 PNG stub for dev
- `apps/api/src/infrastructure/imagegen/factory.py` — `get_image_generator()` by config
- `apps/api/src/infrastructure/imagegen/__init__.py` — module marker

**Video Generation:**
- `apps/api/src/infrastructure/videogen/base.py` — `AbstractVideoGenerator` interface
- `apps/api/src/infrastructure/videogen/ltx_provider.py` — LTX-Video (torch/diffusers, lazy-loaded)
- `apps/api/src/infrastructure/videogen/stub_provider.py` — placeholder mp4
- `apps/api/src/infrastructure/videogen/factory.py` — `get_video_generator()` by config
- `apps/api/src/infrastructure/videogen/__init__.py` — module marker

**Services:**
- `apps/api/src/application/services/response_image_service.py` — builds prompt, calls provider, persists via AttachmentService
- `apps/api/src/application/services/video_generation_service.py` — request/run/get_job for async video jobs

**Domain:**
- `apps/api/src/domain/entities/media_job.py` — `MediaJob` dataclass with properties (`is_terminal`, `is_done`)
- `apps/api/src/domain/repositories/media_job_repository.py` — abstract repo interface

**Infrastructure:**
- `apps/api/src/infrastructure/database/models/media_job.py` — SQLAlchemy ORM model
- `apps/api/src/infrastructure/database/repositories/media_job_repository.py` — concrete implementation
- `apps/api/src/infrastructure/database/migrations/versions/010_media_jobs.py` — **Migration 010**: creates `media_jobs` table, chains 009→010

**API DTOs:**
- `apps/api/src/application/dtos/media.py` — `MediaJobResponse`, `ChapterResponse`

**Frontend (3-pane Layout):**
- `apps/web/features/chat/components/ClassroomChatView.tsx` — 3-pane shell (rail + canvas + panel)
- `apps/web/features/chat/components/SubjectChapterRail.tsx` — Subject→Chapter→Conversation navigation
- `apps/web/features/chat/components/ContextPanel.tsx` — RAG sources + psychographic snapshot
- `apps/web/features/chat/components/VideoAttachment.tsx` — authenticated blob `<video>` player
- `apps/web/features/chat/components/VideoJobCard.tsx` — progress indicator while video runs
- `apps/web/features/chat/components/MessageVideoControl.tsx` — request + poll + player orchestration
- `apps/web/features/chat/hooks/useVideoJob.ts` — polling hook via TanStack Query
- `apps/web/lib/stores/chat.store.ts` — added `streamingImageId` state

**Tests:**
- `apps/api/tests/services/test_media_generation.py` — 9 unit tests (stub providers, service layer, ownership checks)

**Documentation:**
- `docs/ROADMAP.md` — chronological phase history + dependency graph

---

### Modified Files

**Backend Configuration & Dependencies:**
- `apps/api/pyproject.toml` — added `[video]` optional extra (torch, diffusers, transformers, accelerate, imageio, sentencepiece)
- `apps/api/src/config.py` — image_gen_* and video_gen_* config keys, fal_api_key, ltx_model_id, max_concurrent_video_jobs
- `apps/api/src/application/interfaces/dependencies.py` — wired `get_video_generation_service`, injected `response_image_svc` into `get_chat_service`

**Backend Services & Routes:**
- `apps/api/src/application/services/chat_service.py` — added `response_image_svc`/`response_image_enabled` params; image generation overlap logic in `stream_response()`; `get_chapters()` method; chapter filter on `list_conversations()`
- `apps/api/src/presentation/api/v1/chat.py` — added routes: `POST /chat/messages/{id}/video`, `GET /chat/media-jobs/{id}`, `GET /chat/subjects/{subject}/chapters`; chapter query param on `/history`
- `apps/api/src/domain/repositories/conversation_repository.py` — added abstract `chapter_counts()` and chapter filter to `list_by_user()`
- `apps/api/src/infrastructure/database/repositories/conversation_repository.py` — concrete `chapter_counts()` and chapter filter
- `apps/api/src/infrastructure/database/models/__init__.py` — imported `MediaJobModel`, added to `__all__`

**Frontend API & State:**
- `apps/web/lib/api/chat.ts` — added `getChapters()`, `requestVideo()`, `getMediaJob()`
- `apps/web/lib/api/client.ts` — added `fetchAttachmentUrl()` for blob serving (reused by VideoAttachment)
- `apps/web/features/chat/hooks/useChat.ts` — handle SSE `image` event; call `setStreamingImageId()`
- `apps/web/lib/stores/chat.store.ts` — added `streamingImageId` state + setter; reset on new conversation
- `apps/web/features/chat/components/MessageBubble.tsx` — render video attachments; show `MessageVideoControl` if no video yet
- `apps/web/app/(dashboard)/chat/page.tsx` — repointed to `ClassroomChatView`
- `apps/web/app/(dashboard)/chat/[id]/page.tsx` — repointed to `ClassroomChatView`
- `packages/shared/src/dtos/index.ts` — added `MediaJobDto`, `ChapterDto`

---

## Configuration Reference

### Backend Environment Variables

```bash
# Image Generation (Fal)
IMAGE_GEN_ENABLED=true                          # default: true
RESPONSE_IMAGE_ENABLED=true                     # whether to auto-generate on every answer
IMAGE_GEN_PROVIDER=fal                          # fal | stub
FAL_API_KEY=<fal-cloud-key>                     # required if using Fal
IMAGE_GEN_MODEL=fal-ai/flux/schnell             # Fal model ID
IMAGE_GEN_SIZE=1024x1024                        # supported sizes: 512x512, 768x768, 1024x1024

# Video Generation (LTX)
VIDEO_GEN_ENABLED=true                          # default: true
VIDEO_GEN_PROVIDER=ltx                          # ltx | stub
LTX_MODEL_ID=Lightricks/LTX-Video               # HuggingFace model ID
VIDEO_NUM_FRAMES=97                             # default: 97 (consistent with LTX)
VIDEO_FPS=24                                    # default: 24
VIDEO_GUIDANCE_SCALE=3.0                        # guidance scale for generation
MAX_CONCURRENT_VIDEO_JOBS=1                     # GPU semaphore limit (per-process)
```

### Frontend Environment Variables

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000       # backend origin (CORS-enabled)
```

---

## API Reference

### New Endpoints

#### POST `/api/v1/chat/messages/{message_id}/video`

Request on-demand video generation for an assistant message.

**Request:**
```http
POST /api/v1/chat/messages/550e8400-e29b-41d4-a716-446655440000/video HTTP/1.1
Authorization: Bearer <token>
```

**Response (202 Accepted):**
```json
{
  "success": true,
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440001",
    "message_id": "550e8400-e29b-41d4-a716-446655440000",
    "conversation_id": "550e8400-e29b-41d4-a716-446655440002",
    "kind": "video",
    "status": "queued",
    "progress": 5,
    "attachment_id": null,
    "url": null,
    "error_message": null,
    "created_at": "2026-07-04T19:00:00Z",
    "updated_at": "2026-07-04T19:00:00Z"
  },
  "message": "Video generation started"
}
```

#### GET `/api/v1/chat/media-jobs/{job_id}`

Poll the status of a video generation job.

**Request:**
```http
GET /api/v1/chat/media-jobs/550e8400-e29b-41d4-a716-446655440001 HTTP/1.1
Authorization: Bearer <token>
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440001",
    "message_id": "550e8400-e29b-41d4-a716-446655440000",
    "conversation_id": "550e8400-e29b-41d4-a716-446655440002",
    "kind": "video",
    "status": "completed",
    "progress": 100,
    "attachment_id": "550e8400-e29b-41d4-a716-446655440003",
    "url": "/api/v1/chat/attachments/550e8400-e29b-41d4-a716-446655440003",
    "error_message": null,
    "created_at": "2026-07-04T19:00:00Z",
    "updated_at": "2026-07-04T19:01:30Z"
  }
}
```

#### GET `/api/v1/chat/subjects/{subject}/chapters`

List chapters within a subject.

**Request:**
```http
GET /api/v1/chat/subjects/Physics/chapters HTTP/1.1
Authorization: Bearer <token>
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": [
    { "chapter": "Mechanics", "conversation_count": 5 },
    { "chapter": "Thermodynamics", "conversation_count": 2 },
    { "chapter": "Waves", "conversation_count": 3 }
  ]
}
```

#### GET `/api/v1/chat/history?chapter=...` (Modified)

Filter conversation history by chapter (new optional `chapter` query param).

```http
GET /api/v1/chat/history?page=1&limit=20&subject=Physics&chapter=Mechanics HTTP/1.1
```

---

## SSE Event Format (Enhanced)

Chat streaming now includes a new `image` event:

```
data: {"type":"meta","conversation_id":"...","rag":{"has_context":true,"source_count":2,"sources":[...]}}

data: {"type":"chunk","content":"The electromagnetic "}

data: {"type":"chunk","content":"field is..."}

data: {"type":"image","attachment_id":"550e8400-e29b-41d4-a716-446655440003","url":"/api/v1/chat/attachments/550e8400-e29b-41d4-a716-446655440003"}

data: {"type":"done"}
```

The `image` event is emitted **before `done`** if image generation succeeded.

---

## Testing

**Test Suite:** `apps/api/tests/services/test_media_generation.py` — 9 unit tests, all passing.

| Test | Coverage |
|---|---|
| `test_stub_image_generator_returns_png` | Stub provider returns valid PNG bytes |
| `test_stub_video_generator_returns_mp4` | Stub provider returns valid mp4 bytes |
| `test_build_prompt_includes_concept_and_subject` | Prompt building includes context |
| `test_generate_is_fail_open` | Image generator failures return None (never raise) |
| `test_persist_creates_and_links_attachment` | Image persisted and linked to message |
| `test_request_creates_queued_job` | Video request creates queued job |
| `test_request_missing_message_raises` | Video request validates message exists |
| `test_request_wrong_owner_raises` | Video request enforces ownership |
| `test_get_job_ownership` | Job retrieval enforces user ownership |

**Full test suite:** `pytest apps/api/tests/ -v` → **181 passing** (172 baseline + 9 new), no regressions.

---

## Deployment

### Local Development

```bash
# Set environment
export IMAGE_GEN_PROVIDER=stub              # use stubs (no API keys)
export VIDEO_GEN_PROVIDER=stub              # avoid GPU requirement
export RESPONSE_IMAGE_ENABLED=true

# Run migrations
alembic upgrade head

# Start API
uvicorn src.main:app --reload --port 8000

# Start frontend
npm run dev --workspace=apps/web
```

### Production

```bash
# Install video dependencies (on GPU machine)
pip install -e ".[video]"

# Set environment
export FAL_API_KEY=<production-key>
export IMAGE_GEN_PROVIDER=fal
export VIDEO_GEN_PROVIDER=ltx
export RESPONSE_IMAGE_ENABLED=true
export MAX_CONCURRENT_VIDEO_JOBS=4          # scale to GPU vRAM

# Run migrations
alembic upgrade head

# Start API (gunicorn/uvicorn behind proxy)
gunicorn src.main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker
```

---

## Known Limitations

1. **Video runs in-process.** No dedicated worker queue yet. Long video generations block the FastAPI worker thread (mitigated by GPU semaphore). Next: offload to Celery/Bull queue.

2. **No HTTP range/seeking.** Attachment serving is full-body only. MP4 can't seek. Next: implement `Range` header support for streaming long videos.

3. **Image adds ~1–3s per answer.** Overlapped with text (zero added latency perception), but network round-trip is real. Can disable with `RESPONSE_IMAGE_ENABLED=false`.

4. **No media quotas.** Students can request unlimited videos. Next: add daily limits per student, configurable per school.

5. **LTX-Video is slow.** 4–12 seconds for a 97-frame clip on a single A100 GPU. Not suitable for sub-second UX. Next: explore faster models (Runway, SVD-XT) or pre-generated video templates.

---

## How to Extend

### Adding a New Image Provider

```python
# 1. Implement the interface
from src.infrastructure.imagegen.base import AbstractImageGenerator

class MyImageGenerator(AbstractImageGenerator):
    @property
    def provider_name(self) -> str:
        return "myprovider"

    async def generate(self, prompt: str, size: str = "1024x1024") -> ImageResult:
        # Call your API, return bytes
        return ImageResult(data=bytes(...), content_type="image/png")

# 2. Add to factory
def get_image_generator() -> AbstractImageGenerator:
    if settings.image_gen_provider == "myprovider":
        return MyImageGenerator()
    ...

# 3. Update config
class Settings:
    image_gen_provider: Literal["fal", "stub", "myprovider"] = "fal"
```

### Adding Media Quotas

```python
# domain/entities/media_quota.py
@dataclass
class MediaQuota:
    user_id: UUID
    date: date
    video_count: int
    video_count_limit: int = 5  # configurable per school

# Enforce in VideoGenerationService.request()
quota = await quota_repo.get_or_create(user_id, today())
if quota.video_count >= quota.video_count_limit:
    raise QuotaExceededError("Daily video limit reached")
```

### Tracking Generation Metrics

Add telemetry to measure latency + success:

```python
# In ResponseImageService.generate()
import time
start = time.time()
result = await self._generator.generate(prompt, self._image_size)
latency = time.time() - start
metrics.record_image_gen_latency(latency, provider=self._generator.provider_name)
```

---

## Related Documents

- [`docs/ROADMAP.md`](ROADMAP.md) — full platform evolution Phase 0.0 → v0.71
- [`CLAUDE.md`](../CLAUDE.md) — project operating manual, coding standards, architecture
- Memory: [`roognis-verification-auth-gate.md`](../memory/roognis-verification-auth-gate.md)
- Memory: [`v071-generative-multimodal.md`](../memory/v071-generative-multimodal.md)

---

**Handover: Complete** ✅  
**Tests:** 181/181 passing  
**Ruff:** 0 new violations  
**TypeScript:** 0 new errors  
**Committed:** feat/multi-chat-cag (commit 7f7d4bb)
