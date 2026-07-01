# Phase 0.4 — AI Learning Engine

## Overview

Phase 0.4 transforms the RAG chatbot into an AI Learning Engine that builds a persistent model of each student — what they know, where they struggle, and what to study next.

---

## Architecture

```
Chat / RAG Response (streaming)
        │
        ▼  (BackgroundTask — never blocks user)
LearningOrchestrator
        │
        ├── ConceptExtractionService  →  LLM (Groq llama3-8b) → ConceptExtractionResult
        ├── StudentProfileService     →  get_or_create + touch
        ├── SessionMemoryService      →  record LearningSession
        ├── MasteryEngine             →  update MasteryRecord (EMA scoring)
        ├── LearningGapDetector       →  detect/escalate LearningGap from misconceptions
        └── StudentProfileService     →  refresh confidence_score from avg mastery
```

Everything runs asynchronously after the stream completes. Students never wait for it.

---

## Domain Entities

| Entity | Table | Purpose |
|---|---|---|
| `StudentProfile` | `student_profiles` | Persistent per-student settings and velocity metrics |
| `LearningSession` | `learning_sessions` | One record per Q&A interaction with full metadata |
| `ConceptNode` | `concept_nodes` | A single curriculum concept (name + subject + grade) |
| `ConceptEdge` | `concept_edges` | DAG edge: `source` is a prerequisite of `target` |
| `MasteryRecord` | `mastery_records` | 0–100 score per (user, concept) pair |
| `LearningGap` | `learning_gaps` | Detected misconception with severity escalation |

---

## Mastery Algorithm

Scores use **Exponential Moving Average** to prevent single-session spikes:

```
gain        = BLOOM_GAINS[bloom_level]   # Remember:3 → Create:15
penalty     = 15 if misconception else 0
session     = max(0, gain − penalty)
new_score   = min(100, max(0, 0.7 × old + 0.3 × (old + session)))
```

**Labels:** mastered ≥ 85 · developing ≥ 60 · emerging ≥ 30 · not_started < 30

---

## Knowledge Graph

Concepts are stored as a DAG in PostgreSQL (`concept_nodes` + `concept_edges`).

- Edge semantics: `source_id → target_id` means *source is a prerequisite of target*
- Readiness score: fraction of a concept's prerequisites with mastery ≥ 70
- NextBestTopicEngine skips concepts with readiness < 0.5

---

## Learning Gap Severity Escalation

| Occurrence count | Severity | Confidence |
|---|---|---|
| 1 | medium | medium |
| 2 | medium | medium |
| 3 | high | high |
| ≥ 5 | critical | high |

---

## API Endpoints

Base path: `/api/v1/student`

| Method | Path | Description |
|---|---|---|
| GET | `/profile` | Get or create student profile |
| POST | `/profile` | Update grade, subjects, chapter |
| GET | `/sessions` | Paginated session history |
| GET | `/mastery` | All mastery records, sorted by score |
| GET | `/gaps` | Active learning gaps (add `?include_resolved=true`) |
| POST | `/gaps/{id}/resolve` | Mark a gap as resolved |
| GET | `/recommendations` | Top-5 next-best topics |
| GET | `/analytics` | Aggregate stats for the student |

---

## Frontend Pages

| Route | Component | Description |
|---|---|---|
| `/student` | `StudentDashboardView` | Overview: stats, progress bar, quick links |
| `/student/timeline` | `LearningTimelineView` | Chronological session log with Bloom badges |
| `/student/mastery` | `MasteryDashboardView` | Filterable concept mastery cards |
| `/student/graph` | `KnowledgeGraphView` | Concept nodes grouped by mastery tier |
| `/student/gaps` | `WeakAreasView` | Gap cards with severity and resolve action |
| `/student/recommendations` | `RecommendationsView` | Ranked next-best-topic cards |
| `/student/statistics` | `StatisticsView` | Bloom distribution, summary, top/weak concepts |

All pages live under the `(dashboard)` Next.js route group and inherit the sidebar layout.

---

## Files Added / Modified

### Backend (`apps/api/`)
```
src/domain/entities/learning.py
src/domain/repositories/learning_repository.py
src/infrastructure/database/migrations/versions/004_learning_engine.py
src/infrastructure/database/models/learning.py
src/infrastructure/database/repositories/learning_repository.py
src/application/dtos/learning.py
src/application/services/concept_extraction_service.py
src/application/services/student_profile_service.py
src/application/services/session_memory_service.py
src/application/services/mastery_engine.py
src/application/services/knowledge_graph_service.py
src/application/services/learning_gap_detector.py
src/application/services/next_best_topic_engine.py
src/application/services/learning_analytics_service.py
src/application/services/learning_orchestrator.py
src/application/interfaces/dependencies.py          ← extended
src/presentation/api/v1/student.py
src/presentation/api/v1/chat.py                     ← BackgroundTask added
src/presentation/api/router.py                      ← student router added
tests/services/test_mastery_engine.py
tests/services/test_learning_gap_detector.py
tests/services/test_knowledge_graph_service.py
tests/api/test_student_routes.py
```

### Frontend (`apps/web/`)
```
lib/api/student.ts
features/student/components/StudentDashboardView.tsx
features/student/components/LearningTimelineView.tsx
features/student/components/MasteryDashboardView.tsx
features/student/components/KnowledgeGraphView.tsx
features/student/components/WeakAreasView.tsx
features/student/components/RecommendationsView.tsx
features/student/components/StatisticsView.tsx
app/(dashboard)/student/page.tsx
app/(dashboard)/student/timeline/page.tsx
app/(dashboard)/student/mastery/page.tsx
app/(dashboard)/student/graph/page.tsx
app/(dashboard)/student/gaps/page.tsx
app/(dashboard)/student/recommendations/page.tsx
app/(dashboard)/student/statistics/page.tsx
components/layout/Sidebar.tsx                       ← Learning Engine section added
```

---

## Running the Migration

```bash
cd apps/api
alembic upgrade 004
```

---

## Testing

```bash
cd apps/api
pytest tests/services/test_mastery_engine.py       # 12 tests
pytest tests/services/test_learning_gap_detector.py # 8 tests
pytest tests/services/test_knowledge_graph_service.py # 7 tests
pytest tests/api/test_student_routes.py            # 7 tests
```
