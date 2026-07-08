# ADR-012: Cache & FAQ Intelligence Engine

**Status:** Accepted
**Date:** 2026-07-04
**Deciders:** Platform / Backend

## Context

The full-blown HLD specifies a **Cache & FAQ Intelligence** tier (Query Normalizer → Semantic Hash Generator → Hot Query Detector → Cache Policy Manager → Cache Invalidation Controller → FAQ Knowledge Base → In-Memory Cache). The MVP only has `ResponseCacheService` — a flat Redis TTL cache on the RAG path with no hit analytics, no FAQ durability, and no scoped invalidation. When curriculum documents change, stale answers can linger until TTL expiry.

Forces: must stay fail-open (a cache outage must never break answering), reuse the existing Redis client and embedding provider, and fit the clean-architecture monolith (no new infra to deploy for the MVP-to-scale step).

## Decision

Introduce a **`CachingEngine`** application service that composes the HLD boxes as cohesive collaborators and fronts the RAG query path, plus a durable **FAQ Knowledge Base** in Postgres.

- **Query Normalizer** (`QueryNormalizer`): lowercase, strip punctuation, collapse whitespace → stable form.
- **Semantic Hash Generator**: `sha256(normalized_query | scope_json | ns_version)` — scope = curriculum filter; `ns_version` makes invalidation O(1).
- **Cache Policy Manager**: TTL tiers — cold entries get `cache_default_ttl`, entries that cross `cache_hot_threshold` hits get `cache_hot_ttl` (longer).
- **Hot Query Detector**: per-hash Redis counter; crossing `faq_promote_threshold` promotes the (question, answer) into the FAQ KB.
- **FAQ Knowledge Base**: `faq_entries` table (migration 012) — durable, queryable, powers a `/faq` endpoint and analytics.
- **Cache Invalidation Controller**: a per-scope namespace version key (`cache:ver:{scope}`). Bumping it orphans all keys in that scope instantly (lazy eviction). Exposed via an admin endpoint and callable when curriculum changes.

`RagService` receives the `CachingEngine` in place of the plain `ResponseCacheService` (duck-compatible `get`/`set`), so the change is drop-in.

## Options Considered

### Option A: Extend `ResponseCacheService` in place
| Dimension | Assessment |
|-----------|------------|
| Complexity | Low |
| Scalability | Poor — no hot detection / FAQ / invalidation |
| Fit to HLD | Weak |

**Pros:** minimal diff. **Cons:** doesn't realize the HLD tier; no durability or invalidation.

### Option B: `CachingEngine` composing normalizer + Redis + hot detector + invalidation + FAQ KB  *(chosen)*
| Dimension | Assessment |
|-----------|------------|
| Complexity | Medium |
| Scalability | Good — hot promotion, scoped invalidation, durable FAQ |
| Fit to HLD | Strong — maps box-for-box |
| Team familiarity | High — same Redis/SQLAlchemy patterns |

**Pros:** realizes the tier, fail-open, unit-testable with a fake Redis. **Cons:** one new table + service surface.

### Option C: External semantic cache (GPTCache / Redis-VSS)
**Pros:** true vector-similarity cache. **Cons:** new dependency + infra; overkill for the MVP-to-scale step; revisit at high rps.

## Trade-off Analysis

B buys the full HLD tier for the cost of one table and a composed service, while keeping the drop-in `get`/`set` contract. Semantic similarity beyond exact-normalized match (Option C) is deferred: normalization already collapses most phrasing variance, and the FAQ KB captures the durable long tail. Invalidation is lazy (version bump) rather than eager key-scan — O(1) and safe under Redis outage.

## Consequences

- **Easier:** curriculum edits can invalidate stale answers instantly; hot questions become a durable, analyzable FAQ set; cache behavior is observable (`/admin/cache/stats`).
- **Harder:** one more table to migrate; FAQ promotion adds a write on hot hits (bounded, async-safe).
- **Revisit:** true vector-similarity caching (Option C) and document-change-triggered auto-invalidation wiring when write volume grows.

## Action Items
1. [x] Migration 012 `faq_entries`
2. [x] `QueryNormalizer`, `CachingEngine`, `FaqService`
3. [x] Wire `CachingEngine` into `RagService` via DI
4. [x] `/faq` + `/admin/cache/*` routes
5. [x] Unit tests with fake Redis + fake FAQ repo
