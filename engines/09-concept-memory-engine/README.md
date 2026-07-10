# Concept Memory Engine

**Layer:** Teaching history  
**Phase:** 0.5  
**Dependencies:** `structlog`, `pydantic`

## What it does

Maintains a per-(student, concept) teaching journal. Every time a concept is
encountered in a session, it records the teaching approach used and whether
it succeeded (no misconceptions) or failed.

The `ConceptMemory.needs_different_approach` property signals that a concept
has been explained ≥ 3 times with < 50% success — the LLM then receives an
explicit instruction to try a completely different strategy.

## Approach classification

| Bloom level rank | Approach |
|---|---|
| 0–2 (Remember, Understand, Apply) | `procedural` |
| 3–5 (Analyze, Evaluate, Create) | `conceptual` |

## `ConceptMemory` properties

```python
mem.success_rate            # float 0–1
mem.needs_different_approach  # bool (taught ≥3x and success_rate < 0.5)
mem.teaching_notes          # list of last 5 misconception phrases
```

## Integration

```python
from engine import ConceptMemoryService

svc = ConceptMemoryService(memory_repo=..., concept_repo=...)
await svc.record_from_extraction(user_id, extraction, subject="Physics")
struggling = await svc.get_struggling_concepts(user_id)
```

## DB table

`concept_memory` — added in migration 006.
