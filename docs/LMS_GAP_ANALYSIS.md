# LMS Gap Analysis & Implementation Roadmap

Audit date: 2026-07-12 · Scope: `apps/api` backend vs. Google-Classroom-level LMS requirements.

## 1. Audit summary

The backend is a mature FastAPI clean-architecture codebase (domain / application /
infrastructure / presentation) with working auth, RAG, learning analytics, and a
Phase-0.7 classroom module (migration 007). Nothing is a placeholder — but the LMS
surface covers roughly a third of the Google Classroom feature set.

### ✅ Completed modules (preserve as-is)

| Module | Where | Notes |
|---|---|---|
| Auth (register/login/JWT/me) | `auth_service.py`, `v1/auth.py` | JWT HS256, bcrypt, Clerk sync |
| RBAC primitives | `dependencies.py` | `get_current_user`, `require_teacher`, `require_admin` |
| Classrooms (core CRUD) | `classroom_service.py`, `v1/teacher.py` | create/list/get/update/archive, join-code regen |
| Chapters + content upload | same | chapter = KnowledgeBase-backed unit; ingestion pipeline reuse |
| Enrollment (join by code) | `v1/enrollment.py` | join/list/list-chapters |
| Documents/KB/chunks/ingestion | `document_service.py`, models/knowledge.py | full pipeline w/ OCR, embeddings, Qdrant |
| Storage abstraction (local) | `storage/base.py`, `local_storage.py` | ABC exists; only local impl |
| Middleware | `infrastructure/middleware/` | error handler, rate limit, request id, security headers, logging |
| Audit-log **table** | `models/system.py` (`audit_logs`) | table exists since 001; no service/endpoints |
| Sessions **table** | `models/system.py` (`sessions`) | token_hash + expiry — usable for refresh tokens; unused |
| Profiles/settings | `models/profile.py`, `v1/users.py` | avatar_url, bio, preferences |
| Learning/AI stack | 40+ services | out of LMS scope; untouched |

### 🟡 Partially complete (extend, don't rewrite)

| Requirement | Current state | Gap |
|---|---|---|
| Classroom fields | name/subject/section/room/grade/description/color/join_code | missing semester, institution, banner, settings, soft delete, join-code disable |
| Co-teachers | single `teacher_id` owner | no `classroom_teachers` table / invitation flow |
| Enrollment approval | instant join, `status` column exists | no pending/approve/reject flow, no invitations |
| Admin | `require_admin` + vector stats only | no user/institution/classroom management, audit endpoints, storage usage |
| Auth lifecycle | access JWT only | no refresh tokens, password reset, email verification |
| Storage | local only | no S3/R2/MinIO backend, no factory |

### ❌ Missing modules (built in this phase)

1. **Institutions** — entity + admin CRUD, linked from users/classrooms.
2. **Folders & Materials** — nested folders; materials of any file type with category
   (note/assignment/reference/question_paper/solution/other), rename/move,
   soft delete + restore, version history, external links.
3. **Coursework** — announcements, assignments, homework, quizzes, exams,
   practice sets, polls, discussion threads; draft → scheduled → published →
   archived lifecycle; duplicate; attachments; rubric; due dates + late policy;
   optimistic locking.
4. **Submissions** — text + multi-attachment, submit/resubmit/withdraw, late flag.
5. **Grading** — manual scores, rubric scores, comments, private feedback,
   return, regrade (history kept).
6. **Discussions** — nested comments, reactions, mentions, search.
7. **Notifications** — per-user center for both portals; emitted fail-open from
   join/submission/grade/mention/material/announcement events.
8. **Bookmarks + recently viewed / continue learning** — per-student material state.
9. **Dashboards** — teacher analytics (enrollment, completion, averages,
   engagement, inactive students, material usage) and student dashboard
   (deadlines, announcements, progress, bookmarks) — derived, never stored.
10. **Admin backend** — institutions, suspend/delete users, classrooms overview,
    audit-log listing, storage usage.
11. **Auth extensions** — refresh tokens (reuses `sessions` table), password
    reset + email verification (new `auth_tokens` table; pluggable email
    provider with console backend until SMTP is configured).
12. **S3-compatible storage** — one backend covers AWS S3, Cloudflare R2, MinIO
    via `endpoint_url`; selected by `STORAGE_PROVIDER`.

## 2. Design decisions

- **One migration** — `009_lms_core` (explicit, no autogenerate), next in sequence.
- **Rubrics as JSONB** on coursework; rubric scores as JSONB on grades. A separate
  rubric table adds joins without behavior — criteria are always read whole.
- **Regrade = new grade row** — grade history is append-only; latest wins.
- **Optimistic locking** — integer `version` on coursework + materials; updates carry
  the expected version and 409 on mismatch.
- **Soft deletes** — `is_deleted`/`deleted_at` on classrooms, folders, materials,
  coursework, comments. Hard delete stays admin-only.
- **Notifications are fail-open** — emission failures are logged, never break the
  triggering request (same principle as the learning pipeline).
- **Materials reuse `documents` storage fields** where uploaded through ingestion, but
  material files themselves store via the storage factory (no chunking needed for
  videos/ZIPs); `material_versions` keeps prior file paths.
- **Existing routes unchanged** — everything is additive; old clients keep working.

## 3. Roadmap (implementation order)

1. Foundations: domain entities → ORM models → migration 009
2. Repositories (abstract + concrete)
3. Auth extensions + storage factory (independent of 1–2)
4. Classroom extensions (co-teachers, invitations, approvals, soft delete)
5. Materials (folders, versions, restore, bookmarks, views)
6. Coursework lifecycle
7. Submissions + grading
8. Discussions
9. Notifications (then wired into 4–8)
10. Dashboards/analytics
11. Admin backend
12. DI wiring, router, ruff, tests
