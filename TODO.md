# Roognis AI — Task List

Last updated: 2026-07-03 (after Phase 0.5 commit `097efbb`)

---

## High Priority

- [ ] **Seed curriculum knowledge graph** — populate `concept_nodes` and `concept_edges` with real CBSE/NCERT curriculum data for at least 2 subjects (e.g., Mathematics and Physics) and 2 grades. Without this data, the `/student/learning-path` and frontier features return empty results. Update `scripts/seed.py` or create `scripts/seed_curriculum.py`.

- [ ] **Fix bcrypt/passlib version conflict** — in `apps/api/pyproject.toml`, change `"bcrypt==3.2.2"` to `"bcrypt>=4.0.0"`. Reinstall and verify the 3 currently-failing auth tests (`test_register_success`, `test_login_success`, `test_login_wrong_password`) now pass. Total test count should reach 159 passing, 0 failing.

- [ ] **Test LearningPath + Frontier end-to-end** — after seeding concept nodes/edges, manually test `GET /student/learning-path` with a `target_concept_id` query param and verify the returned `path` and `frontier` are correctly ordered by topological sort. Test with a student who has some mastery records and some gaps.

---

## Medium Priority

- [ ] **Add pagination to `GET /student/memory`** — the concept memory endpoint currently returns all records for a user with no pagination. Add `page` and `limit` Query params (pattern matches `/student/sessions`). Update `ConceptMemoryService.get_all()` to accept `limit` and `offset`, update the repository `list_by_user()` accordingly.

- [ ] **Make session limit configurable in `GET /student/skills`** — `get_skill_profile()` hardcodes `limit=50` when fetching sessions. Add `session_limit: int = Query(default=50, ge=10, le=200)` query param so consumers can request more sessions for a more accurate Bloom distribution.

- [ ] **Add `_frontier_reason()` UI indicator for cap truncation** — when `path_to_concept()` truncates at 10 nodes or `get_frontier()` truncates at 8, the frontend should show "Showing top N of M available" text. Backend: add `total_available` field to `LearningPathResponse` and `frontier_total` field. Frontend: render the count in `LearningPathView.tsx`.

- [ ] **Frontend: wire `LearningPathView` concept click → `target_concept_id`** — currently `LearningPathView.tsx` calls `getLearningPath()` without a `target_concept_id`. Add a concept picker (dropdown or text input) that lets the student select a concept by name, resolves it to a UUID (via `/student/mastery` or a new concept search endpoint), and re-queries with `target_concept_id`.

- [ ] **Add concept search endpoint** — `GET /knowledge/concepts?q=<search_term>&grade=<grade>&subject=<subject>` — queries `ConceptNodeRepository` for nodes matching the search term. Needed by the frontend concept picker in `LearningPathView`.

- [ ] **Phase 0.6 planning** — decide between: (a) adaptive quiz/assessment system with IRT scoring, (b) teacher/parent dashboard, (c) multi-persona roles. Document the decision in `DECISIONS.md`.

---

## Low Priority

- [ ] **Refactor `learning_order()` to use `collections.deque`** — in `apps/api/src/application/services/knowledge_graph_service.py`, the `queue.pop(0)` call is O(n). Replace `list` with `collections.deque` and `popleft()` for O(1). No behavioral change; purely a performance improvement for large graphs.

- [ ] **Type `concept_memory_svc` properly in `LearnerContextService`** — currently typed as `Any` to avoid circular imports. The clean solution is to define a `Protocol` (e.g., `ConceptMemorySvcProtocol`) in `domain/repositories/` with `get_struggling_concepts(user_id)` as the only method, and use that Protocol as the type hint.

- [ ] **Production Docker images** — create a multi-stage Dockerfile for `apps/api` (build stage: install deps; runtime stage: minimal image). Update `docker-compose.yml` to use it. Add healthcheck commands.

- [ ] **CI/CD pipeline** — add `.github/workflows/ci.yml` that runs `ruff check apps/api/` and `pytest apps/api/tests/ -v` on every push to `main` and every PR.

- [ ] **End-to-end test for chat + learning pipeline** — write a Playwright test (or pytest with httpx for API-only) that: logs in, sends a chat message, waits for streaming to complete, then asserts the background pipeline ran by checking `/student/sessions` has a new entry with the correct `intent`.

- [ ] **`scripts/seed.py` documentation** — document what `scripts/seed.py` seeds and how to run it in `docs/DEVELOPMENT.md`. Add a step to `README.md` that includes seeding as part of the initial setup.

- [ ] **Remove or document `Roognis_Ai_Backend_repo/`** — this directory appears in `git status` as untracked. Either `.gitignore` it or clarify its purpose. Do not commit without understanding its contents.

- [ ] **Stale docs audit** — review `docs/*.md` files. Some (e.g., `docs/phase-0.4-learning-engine.md`) may be outdated relative to Phase 0.5 changes. Update or mark as historical.
