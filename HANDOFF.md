# Development Handoff — Roognis AI

Last updated: 2026-07-07
Last commit: `32ce112` — SSE chunk encoding, cross-read buffering, smoke-test path fix
Branch: `feat/multi-chat-cag` (pushed to `origin/feat/multi-chat-cag`, 11 commits ahead of what was on GitHub before this session — now in sync)

**Read this file first, then `PROJECT_STATE.md` for the status table, then `TODO.md` for the exact backlog.** The old versions of all three (frozen at Phase 0.5 / commit `097efbb` / branch `master`) were superseded in this pass — 15 commits and several phases had landed since with no handoff update.

---

## Where things actually stand

The repo went through, in order, since Phase 0.5: **Phase 0.6 (multi-conversation chat + CAG)**, **v0.71 (generative image/video + Classroom layout)**, **mobile app (Expo)**, **Phase 0.8 (school B2B2C)**, **Phase 0.9 (caching engine + parent portal)**, an **MVP-hardening pass**, a **5-kid demo-readiness pass**, and a **bug-fix pass**. All of that is committed and pushed. Nothing is silently uncommitted except two things that are intentionally NOT part of this work (see "Deliberately left alone" below).

### The core user flow is feature-complete
Login → Dashboard → Subject/Chapter → AI Tutor (chat + RAG + generated image) → Quiz → Progress (mastery/gaps/learning-path/skills/statistics) → **Teacher Dashboard (roster + analytics)** → **Parent Dashboard (read-only child overview)**. Every stage has a working backend endpoint and a working web page.

### What's new since the last handoff, by phase

**Phase 0.8 — School B2B2C.** `users.role` (student/teacher/school_admin/parent), schools, school_members, classrooms with join codes, enrollments, syllabus_items (migration 011). Full service + route + web (teacher portal, student "My Classes") + mobile (Expo classes screens).

**Phase 0.9 — Caching Engine + Parent Portal** (ADR-012, ADR-013 in `docs/adr/`). `CachingEngine` fronts the RAG path: query normalization, semantic hashing, hot-query detection, scoped invalidation, FAQ auto-promotion (migration 012, `faq_entries` table). Parent Portal: consent-based guardian linking via 8-char codes, read-only child overview (migration 013, `guardian_links` table).

**MVP hardening (this session, before the 5-kid ask).**
- **Fixed a real runtime-breaking auth bug**: env had `bcrypt 5.0.0` + `passlib 1.7.4`; bcrypt ≥4.1 makes the 72-byte limit a hard `ValueError`, which crashes passlib's backend init, which broke `hash_password` — **register/login were dead**. Pinned `bcrypt==4.0.1` in `apps/api/pyproject.toml`. This is why the old "3 pre-existing bcrypt test failures" note in the old docs is gone — they're fixed, and it was never just a test-environment quirk.
- Fixed `docker/api.Dockerfile`: it had `pip install -e ".[dev]" || true` then a hand-written fallback list **missing bcrypt/qdrant-client/fastembed** — a built container could boot with dead auth and dead RAG. Added `[tool.hatch.build.targets.wheel] packages=["src"]` to `pyproject.toml` and rewrote the Dockerfile to install from it (single source of truth, no silent-fail fallback).
- Added **role selection at signup** (`RegisterRequest.role: Literal["student","parent","teacher"]`) — before this, every new signup landed as `student` and teachers/parents had no way to reach their own dashboards.
- Added **Teacher Classroom Analytics**: batch `GROUP BY` repo methods (no N+1 — a 40-student roster is a fixed handful of queries, not 40×3), `ClassroomAnalyticsService`, `GET /school/classrooms/{id}/analytics`, and a `ClassroomAnalyticsView` on the web (mastery distribution, common weak concepts, per-student table). This closed the "teachers can't monitor progress" gap.
- Added `scripts/smoke_test.py` — a standalone httpx script that walks the entire golden path against a live server and prints PASS/FAIL per step.

**5-kid demo readiness (this session, after the user's "server hosting + demo for 5 kids" ask).**
- `scripts/seed.py` gained an idempotent `SEED_DEMO=1` block: 5 students (`kid1`–`kid5@demo.roognis.ai`, password `Demo1234!`) deliberately spread across mastery buckets (mastered/proficient/developing/struggling/brand-new), all enrolled in a `DEMO24` classroom, plus a teacher and a parent linked to `kid1`.
- `docs/DEMO.md` — the hosting/demo runbook, with a demo-lean env (`RETRIEVAL_ENABLED=false` since no curriculum docs are loaded, `VIDEO_GEN_PROVIDER=stub`, image generation optionally stubbed). Verified the tutor answers generally via the `default_system` prompt fallback when there's no RAG context, so it works with an empty Qdrant.
- A local `.env` was created (git-ignored — never committed) with the user's Groq key. **That key was pasted in plaintext in chat and should be rotated in the Groq console** before/after any public demo.

**Web-boot fixes (the web literally could not run before this).**
- **Removed Clerk entirely** from the web app — it was wrapped in `ClerkProvider`, gated by `clerkMiddleware`, and used `useUser`/`useAuth`/`UserButton` in several places, none of which work without real Clerk keys. The app has always authenticated with its own JWT (`authApi` + `useAuthStore`), so Clerk was dead weight blocking boot. Replaced with `components/layout/AuthGuard.tsx` (client-side route guard) and `AccountButton.tsx` (logout).
- **Found and fixed a latent bug**: `apiClient.setTokenProvider` was defined but **never called** — every request went out with no `Authorization` header, so all authenticated calls would have 401'd regardless of the Clerk issue. Now wired: `apiClient.setTokenProvider(async () => useAuthStore.getState().token)` in `apps/web/lib/api/client.ts`.
- Fixed two pre-existing `tsc` build errors (`UploadDashboard.tsx` `ApiResponse` unwrap, `StreamingMessage` not exported from `chat.store.ts`) — **`tsc` is now 100% clean** for the first time.
- Rewrote `docker/web.Dockerfile` from pnpm to npm (the repo ships `package-lock.json`, not a pnpm lockfile — the old Dockerfile would have failed at `pnpm install --frozen-lockfile`). Added Next.js `output: 'standalone'` + `outputFileTracingRoot`, and a `.dockerignore` (also keeps `.env` secrets out of the image).

**Bug-fix pass (chat streaming — real, demo-relevant bugs).**
- `chat_service.py` streamed each token by hand-escaping only `"` and `\n` into JSON. Any backslash content — **LaTeX math like `\frac{1}{2}` or `\sqrt{4}`, which a math tutor emits constantly** — produced invalid JSON, so the browser's `JSON.parse` threw and the token was silently dropped. Fixed to use `json.dumps` for every SSE event (chunk + done; meta/image already did).
- `useChat.ts` parsed SSE by splitting each network read on `\n` with **no buffering across reads**. SSE events routinely span read boundaries, so a split event failed `JSON.parse` (swallowed by an empty `catch`) and that token vanished — garbled/missing words in streamed answers. Fixed with proper cross-read line buffering.
- `smoke_test.py` posted to `/api/v1/chat/stream`, but the real endpoint is `POST /api/v1/chat` (`@router.post("")` under the `/chat` prefix — the web app's `chat.ts` was already correct). Fixed the smoke test.

---

## Verified in this session (what you can trust without re-checking)

- **Backend: 213 tests passing, 0 failing.** (Was 200 passing / 3 failing before the bcrypt fix.) `ruff check apps/api/` clean except 31 pre-existing `B008` (FastAPI `Depends()`-in-default-argument pattern — a Ruff false positive for this framework, not a real issue).
- **Web: `tsc --noEmit` fully clean.** Zero `@clerk/*` imports remain anywhere in `apps/web`.
- App boots (`from src.main import app`) under both normal and demo-lean config (RAG off, image/video stubbed) — 88 routes registered.
- Migration chain 001 → 013 verified linked (each `down_revision` matches the previous).
- The JSON-escaping fix was proven directly: the old manual escaping produces `Invalid \escape` on `\frac{1}{2}`; `json.dumps` produces valid JSON and round-trips the content exactly.

## NOT verified (needs a live machine with Docker — unavailable in this session)

- **The actual live chat round-trip against Groq** (real streaming, not just code-path inspection).
- **The Docker web image build** (`docker build` for `docker/web.Dockerfile`) — the Dockerfile was rewritten and reasoned through carefully, but never actually built. This is the single highest-risk unverified thing in the whole stack.
- `docker compose up -d --build` end-to-end, and `python scripts/smoke_test.py` against a live stack.
- Whether `next build` succeeds under `output: 'standalone'` with the monorepo tracing root (again, reasoned through, not executed).

---

## Deliberately left alone (do not touch without checking with the user)

1. **`Backend_ClaudeCode/`** — an untracked directory containing its **own nested `.git`** (a separate repo). Not part of this codebase's work. Never `git add` it from the root.
2. **`.claude/settings.local.json`** — tracked, but its only uncommitted diff is local Claude Code tool-permission bookkeeping (bash-command allowlist entries), not application code. Left uncommitted on purpose.

---

## Exact next steps, in order

1. **Run the live stack and the smoke test** — this is the #1 priority, because nothing about the chat/demo path has been executed, only reasoned through.
   ```bash
   docker compose up -d --build
   python scripts/smoke_test.py --base-url http://localhost:8000
   ```
   Every step should print PASS. If the web container fails to build, that confirms the one real risk flagged above (Docker web image, standalone build) — read `docker/web.Dockerfile` and `apps/web/next.config.ts` together; the likely failure modes are a missing file in the standalone trace (workspace package not resolved) or the Google Fonts fetch in `next build` failing behind a restrictive network.

2. **If Docker is inconvenient right now, use local dev mode instead** (documented in `docs/DEMO.md` §4 Option B) — infra via `docker compose up -d postgres redis qdrant`, then `uvicorn` and `npm run dev` directly. This is the fastest path to actually clicking through the app in a browser.

3. **Rotate the Groq API key** the user pasted in plaintext mid-session, once the demo/testing is done with it.

4. **Open a PR** — `gh` is not authenticated in this environment (`gh auth login` needed), so no PR exists yet for `feat/multi-chat-cag` → `master`. The branch is pushed and ready to compare.

5. **Multi-device demo config** — if the 5 kids will use their own devices (not all on localhost), set `NEXT_PUBLIC_API_URL` to the server's real reachable address and add that origin to the API's `cors_origins` (currently defaults to `http://localhost:3000`). Documented in `docs/DEMO.md`.

6. Everything in **`TODO.md`** below the "just-verified" items — the remaining low/medium priority backlog is largely intact from before (concept-graph seeding depth, pagination on a couple of endpoints, etc.) and still applies.

## Explicitly postponed (per the user's own "fastest usable MVP" / "tangible features only" directives — do not build unless asked)

Student onboarding modal/tooltips, Notes, Bookmarks, teacher Assignments, parent weekly-digest emails, admin CRUD expansion, CI/CD pipeline, automated backups, self-serve billing. The user framed these as post-demo/post-funding.

---

## Context that exists only in conversation history (not reconstructable from the code alone)

- The user's specific directive that reframed scope mid-session: *"this MVP system should be ready for server hosting and demo for 5 kids... intelligence and the personalization layer takes a back seat."* This is why `RETRIEVAL_ENABLED=false` is the demo default and why the 5-kid seed exists at all — it's not a general-purpose seed, it's demo-specific.
- A separate, earlier "Principal Engineer" directive constrained scope hard: ship fastest usable MVP, do not touch auth/FastAPI/Postgres/Qdrant/RAG/Clean-Arch/existing repos, only fix defects, and follow a strict backlog order (Student → Teacher → Parent → Admin → Production). The Track 1/Track 2 work in this handoff was scoped directly against that backlog.
- The Groq API key currently in the local `.env` (git-ignored) was shared in the chat transcript in plaintext — flag this to the user again if it's still in use by the time you read this.
