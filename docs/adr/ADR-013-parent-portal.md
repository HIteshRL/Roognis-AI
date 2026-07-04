# ADR-013: Parent Portal (Parent Persona)

**Status:** Accepted
**Date:** 2026-07-04
**Deciders:** Platform / Product

## Context

The HLD has a **Parent Persona** (locked in the MVP) fed by the Parent/Teacher Feed Generator and alerts. The MVP has no guardian concept. We need parents to get a **read-only** view of their child's learning (mastery, gaps, streak, recent activity, weekly digest) without exposing other students' data and without a heavyweight invite/approval system.

Forces: student privacy + consent, reuse of existing learning-analytics/mastery/gap/session services, the existing `users.role` column (Phase 0.8), fail-open, minimal new surface.

## Decision

Add a **consent-based guardian link** modeled on the Phase 0.8 classroom join code:

- A **student generates a link code** (short-lived, stored in Redis with TTL). The code is theirs to share — no PII lookup by the parent.
- A **parent submits the code** to create a durable `guardian_links` row (Postgres). On first successful link the parent's `role` is promoted to `parent` (never demoting a stronger role).
- Parents get **read-only** child endpoints; every child endpoint verifies an **active guardian link** between the caller and that student.
- The **child overview** is composed from existing services (`LearningAnalyticsService`, mastery/gap/session repos) — no new analytics, "derive don't store." A **weekly digest** is computed from the last 7 days of sessions + mastery.

Students can list and **revoke** their linked guardians at any time.

## Options Considered

### Option A: Student-generated share code (chosen)
| Dimension | Assessment |
|-----------|------------|
| Complexity | Low |
| Privacy | Strong — consent-based, no email lookup |
| Reuse | High — mirrors classroom join-code flow |

**Pros:** consent by construction; no cross-account enumeration; student controls + revokes. **Cons:** requires the student to share a code out-of-band.

### Option B: Parent invites child by email
**Pros:** familiar. **Cons:** needs a child-side approval inbox + email plumbing; enables enumeration; more surface.

### Option C: School/teacher assigns the parent link
**Pros:** fits B2B2C admin. **Cons:** needs admin UI + roster mapping; defer to a later school-admin phase.

## Trade-off Analysis

A is the smallest consent-correct design and reuses the exact code-issuance pattern already shipped for classrooms. It avoids the enumeration risk of email-based linking (B) and the admin dependency of assignment (C). The link code lives in Redis (ephemeral, TTL) while the relationship lives in Postgres (durable) — the same split used elsewhere.

## Consequences

- **Easier:** parents get a safe, revocable read-only view reusing all existing analytics; opens the Parent/Teacher feed + alerts work later.
- **Harder:** every child endpoint must enforce the guardian-link check (centralized in `ParentService.assert_linked`).
- **Revisit:** email/SMS weekly-digest delivery + push alerts (needs the Notification Service box); school-assigned links (Option C); mobile parent screens.

## Action Items
1. [x] Migration 013 `guardian_links`
2. [x] `GuardianLink` entity/repo/model
3. [x] `ParentService` (code issue/redeem, children, overview, digest, revoke)
4. [x] `/parent` routes + `require`-linked checks + role promotion
5. [x] Web: parent portal + student "Family Access" (share/revoke)
6. [x] Unit tests (link flow, overview auth, revoke)
7. [ ] (Deferred) mobile parent screens; email/push digest delivery
