# Roognis AI — Task List

Last updated: 2026-07-07 (after commit `32ce112`, branch `feat/multi-chat-cag`)

Superseded a Phase-0.5-era version of this file that predated 15 commits of work (Phase 0.6, v0.71, mobile, Phase 0.8, Phase 0.9, MVP hardening, 5-kid demo, web-boot fixes, chat bug fixes). See `HANDOFF.md` for the full narrative.

---

## High Priority — do these first

- [ ] **Run the stack live and execute `scripts/smoke_test.py`.** Nothing in the chat/demo path has been executed end-to-end in the last several sessions — only reasoned through and unit-tested. `docker compose up -d --build && python scripts/smoke_test.py --base-url http://localhost:8000`. Every step should print PASS.

- [ ] **Confirm the web Docker image actually builds.** `docker/web.Dockerfile` was rewritten this session (pnpm → npm, added `output: 'standalone'` + `outputFileTracingRoot` in `apps/web/next.config.ts`, added `.dockerignore`) but never run through `docker build`. This is the single highest-risk unverified change in the repo. If it fails, check: (a) whether the standalone trace correctly bundles `packages/shared` and `packages/ui`, (b) whether `next build` can reach Google Fonts over the network from inside the build container (the app uses `next/font/google`).

- [ ] **Rotate the Groq API key.** It was shared in plaintext in a chat message this session and is now sitting in a local, git-ignored `.env`. Regenerate it in the Groq console once current testing/demo use is done, and update `.env`.

- [ ] **Open a PR for `feat/multi-chat-cag` → `master`.** `gh auth login` is required first (not authenticated in the current environment) — once that's done, `gh pr create` or the GitHub web UI. The branch is already pushed and in sync with origin.

- [ ] **If demoing across multiple devices**, set `NEXT_PUBLIC_API_URL` to the server's real reachable address (not `localhost`) and add that web origin to the API's `cors_origins` config. Documented in `docs/DEMO.md`.

---

## Medium Priority

- [ ] **Verify the live Groq streaming round-trip renders correctly in the browser**, specifically with math content (the two SSE bugs fixed this session — manual JSON escaping and missing cross-read buffering — were both triggered by realistic math-tutor output like `\frac{1}{2}`). A manual click-through asking the tutor a fractions question is the fastest check.

- [ ] **Decide on real vs. stub image generation for the demo.** Currently `IMAGE_GEN_PROVIDER=stub` in the local `.env` (no Fal key was provided). If real illustrations are wanted under each answer, get a Fal API key, set `FAL_API_KEY` + `IMAGE_GEN_PROVIDER=fal` + `RESPONSE_IMAGE_ENABLED=true`.

- [ ] **Seed a deeper curriculum knowledge graph** if the demo needs more than Grade-8 Math fractions/decimals/ratios. Currently `SEED_DEMO=1` seeds ~10 concept nodes in one cluster — fine for a 5-kid fractions demo, thin for anything broader.

- [ ] **Add pagination to `GET /student/memory`** — still returns all concept-memory records for a user with no limit/offset. Long-standing item, low urgency at demo scale.

- [ ] **Make the session limit configurable in `GET /student/skills`** — hardcodes `limit=50` when fetching sessions for Bloom distribution. Long-standing item.

- [ ] **Frontend: wire a concept picker into `LearningPathView`** so a student can pick a `target_concept_id` instead of the endpoint always defaulting. Long-standing item, not demo-blocking.

---

## Low Priority

- [ ] **CI/CD pipeline** (`.github/workflows/ci.yml` running `ruff check` + `pytest` + `tsc`) — explicitly postponed per the "fastest usable MVP" directive; revisit post-demo.

- [ ] **Automated backups** for Postgres — postponed, same reason.

- [ ] **Self-serve billing** — postponed; B2B sales is invoice-led at this stage per the user's own framing.

- [ ] **Student onboarding modal + contextual tooltips** — postponed; explicitly out of scope for a "tangible features only" demo.

- [ ] **Notes, Bookmarks, teacher Assignments, parent weekly-digest email** — all postponed per directive; not part of the core sellable flow.

- [ ] **Refactor `learning_order()` to use `collections.deque`** instead of `list.pop(0)` — O(n) → O(1), only matters at large concept-graph scale. Long-standing, cosmetic.

- [ ] **Type `concept_memory_svc` properly in `LearnerContextService`** (currently `Any` to dodge a circular import) — long-standing, cosmetic, documented as an intentional trade-off in `CLAUDE.md`.

- [ ] **Stale-docs audit** — `docs/phase-0.4-learning-engine.md` and the two `docs/HANDOVER_*.md` files are historical/phase-specific and were not touched this session; they're accurate for their phase but could use a "historical, see HANDOFF.md for current state" banner.

---

## Known Non-Issues (do not re-investigate)

- **31 Ruff `B008` warnings** in `apps/api/` — FastAPI's `Depends()`-as-default-argument pattern deliberately triggers this; it's the correct FastAPI idiom, not a bug.
- **`@clerk/nextjs` still listed in `apps/web/package.json`** — unused after this session's Clerk removal, left in to avoid unnecessary lockfile churn. Harmless; safe to remove in a future cleanup pass.
- **`Backend_ClaudeCode/`** at the repo root has its own nested `.git` — it's a separate workspace, not part of this codebase. Do not `git add` it.
