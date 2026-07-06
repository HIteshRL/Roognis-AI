# Project State Snapshot — Roognis AI

**Date:** 2026-07-07
**Last commit:** `32ce112` — SSE chunk encoding, cross-read buffering, smoke-test path fix
**Branch:** `feat/multi-chat-cag` (pushed to origin, in sync)

---

## Overall Completion: ~80% of MVP core flow

The full core flow (Login → Dashboard → Subject/Chapter → AI Tutor → Quiz → Progress → Teacher Dashboard → Parent Dashboard) has a working backend + web page at every stage. What's unverified is *live execution* (Docker build, real Groq round-trip) — not missing features. See `HANDOFF.md` for the exact unverified list.

---

## Backend Status

| Component | Status | Notes |
|-----------|--------|-------|
| FastAPI scaffold + middleware | Complete | Auth, rate limiting, CORS, metrics |
| PostgreSQL ORM (async) + migrations | Complete | 001 → 013, verified linked |
| JWT authentication | Complete | Register (with role selection), login — **auth bug fixed this session** (bcrypt 5.0.0/passlib 1.7.4 conflict was crashing hash_password) |
| Streaming chat (SSE) | Complete | `POST /api/v1/chat` — **2 encoding bugs fixed this session** (manual JSON escaping, missing cross-read buffering on the client) |
| Groq LLM integration | Complete | Not yet exercised live in this session |
| RAG pipeline | Complete | Off by default for the demo (`RETRIEVAL_ENABLED=false`) — tutor falls back to general answers with no curriculum loaded |
| Concept extraction / mastery / gaps / orchestrator | Complete | Unchanged since Phase 0.5, still fail-open background pipeline |
| Knowledge graph / learning path / skills | Complete | Unchanged since Phase 0.5 |
| **School B2B2C** (schools, classrooms, join codes, syllabus) | Complete | Phase 0.8 |
| **Caching Engine + FAQ** | Complete | Phase 0.9, ADR-012 |
| **Parent Portal** (guardian links, child overview) | Complete | Phase 0.9, ADR-013 |
| **Teacher Classroom Analytics** | Complete | This session — batch aggregate queries, no N+1 |
| Role at signup | Complete | This session — was previously hardcoded to `student` |
| Generative image/video (v0.71) | Complete | Image real (Fal) or stub; video always stub for the demo (no GPU) |
| Multi-conversation chat + CAG | Complete | Phase 0.6 |
| Adaptive assessment (IRT scoring) | Not started | Was suggested Phase 0.6, superseded by other priorities |
| Admin CRUD expansion | Not started | Explicitly postponed per directive |
| CI/CD pipeline | Not started | Explicitly postponed per directive |

---

## Frontend Status (Web)

| Component | Status | Notes |
|-----------|--------|-------|
| Next.js 15 App Router | Complete | **Clerk removed entirely this session** — was blocking boot without real Clerk keys; app already used its own JWT |
| Custom JWT auth (login/register + role select) | Complete | `AuthGuard` (route protection) + `AccountButton` (logout) replace Clerk's middleware/UserButton |
| API client → JWT wiring | **Fixed this session** | `setTokenProvider` was defined but never called — every request went out unauthenticated (would 401) |
| Chat interface (streaming, markdown, images) | Complete | SSE parsing bug fixed this session (cross-read buffering) |
| Student dashboard, mastery, gaps, learning path, skills, statistics, timeline | Complete | Unchanged since Phase 0.5 |
| My Classes (student), Teacher Portal, Classroom Analytics | Complete | Phase 0.8 + this session |
| Parent Portal, Family Access (guardian codes) | Complete | Phase 0.9 |
| `tsc --noEmit` | **Fully clean** | First time — 2 pre-existing build errors fixed this session |
| Web Docker image | **Unverified** | Dockerfile rewritten (pnpm→npm, standalone output) but never actually built |
| Student onboarding / tooltips | Not started | Explicitly postponed |

---

## Database Status: All Migrations Applied, Chain Verified

| Migration | Description |
|-----------|--------------|
| 001–006 | Users/auth → RAG → curriculum RAG → learning engine → behavioral signals → intent/concept-memory (Phase 0.5 and earlier) |
| 007–010 | Multi-conversation/CAG, multimodal attachments, media jobs (Phase 0.6 / v0.71) |
| 011 | School B2B2C: schools, school_members, classrooms, enrollments, syllabus_items |
| 012 | FAQ cache (`faq_entries`) |
| 013 | Guardian links (`guardian_links`) |

**Next migration:** `014` — none currently required.

---

## Testing Status: 213/213 Passing (0 failing)

Was 200 passing / 3 failing (bcrypt/passlib version conflict) before this session's fix. `ruff check apps/api/` clean except 31 pre-existing `B008` (FastAPI DI pattern, not a real issue). `tsc --noEmit` on the web app is fully clean.

No live end-to-end run has happened yet — `scripts/smoke_test.py` exists and is correct (path bug fixed this session) but has not been executed against a running stack in this environment.

---

## Deployment Status

| Item | Status |
|------|--------|
| Docker Compose (postgres/redis/qdrant/api/web/nginx) | Written, `env_file: .env` wired, seed-on-boot via `SEED_DEMO` | **not run in this session** |
| API Dockerfile | Fixed this session (installs from `pyproject.toml`, no silent-fail fallback) — not built |
| Web Dockerfile | Rewritten this session (npm, standalone output) — **not built, highest-risk unverified item** |
| Demo dataset (5 students + teacher + parent) | Seeded via `SEED_DEMO=1`, idempotent | not run in this session |
| Local `.env` with real Groq key | Created (git-ignored) | key was shared in plaintext chat — rotate after use |
| Staging/production environment | Not configured | out of current scope |
| CI/CD | Not configured | explicitly postponed |

---

## Documentation Status

| Document | Status |
|----------|--------|
| `HANDOFF.md` | **Rewritten this session** — was frozen at Phase 0.5 |
| `PROJECT_STATE.md` | **This file, rewritten this session** |
| `TODO.md` | **Rewritten this session** |
| `CHANGELOG.md` | Appended this session with a consolidated entry for everything since 0.5.0 |
| `DECISIONS.md` | Appended this session with the auth-fix, Clerk-removal, and demo-config decisions |
| `CLAUDE.md` | Current — still accurate as the operating manual |
| `docs/DEMO.md` | Current — hosting + demo runbook, written this session |
| `docs/ROADMAP.md` | Current — has a Phase 1.0 section added this session |
| `docs/adr/ADR-012`, `ADR-013` | Current |
| `docs/HANDOVER_MOBILE_EXPO.md`, `docs/HANDOVER_v071_GENERATIVE_MULTIMODAL.md` | Historical, phase-specific — not updated, still accurate for their phase |

---

## Where the Next Claude Session Should Begin

**Read `HANDOFF.md` first** — it has the full "what changed, what's verified, what isn't" narrative and the exact next-steps list.

**The single highest-value first action:** run the stack live and execute the smoke test.
```bash
docker compose up -d --build
python scripts/smoke_test.py --base-url http://localhost:8000
```
This is the one thing that turns "reasoned through carefully" into "actually confirmed working" — nothing in this codebase has been executed end-to-end in this session, only unit-tested and statically verified. If Docker isn't convenient, `docs/DEMO.md` §4 Option B has a local-dev path (`uvicorn` + `npm run dev`) that's faster to iterate on.

If the smoke test (or a manual click-through) surfaces a failure, the highest-suspicion areas — in order — are: (1) the web Docker image build (never actually built), (2) the live Groq streaming round-trip (never actually exercised), (3) anything in `next.config.ts`'s `outputFileTracingRoot` / monorepo package resolution.
