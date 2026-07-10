# Learning Orchestrator

**Layer:** Pipeline coordinator  
**Phase:** 0.3 (extended through 0.5)  
**Dependencies:** `structlog`, `pydantic` + all other engines

## What it does

The orchestrator is the "glue" that runs after every chat response is sent.
It sequences all other learning engines in the correct order and guarantees
the pipeline never fails the user — every exception is caught, logged, and
swallowed.

## Pipeline sequence

```
1. ConceptExtractionService   → extract(question, ai_response) → ConceptExtractionResult
2. StudentProfileService      → get_or_create, touch last_active
3. SessionMemoryService       → record session to DB
4. MasteryEngine              → update_from_extraction
5. LearningGapDetector        → process_extraction
6. (auto-resolve)             → resolve gaps where mastery ≥ 85
7. StudentProfileService      → refresh_confidence (avg mastery)
8. LearningVelocityService    → compute_velocity → update_velocity
9. LearnerBehaviorService     → compute → update_behavioral_signals
10. ConceptMemoryService      → record_from_extraction
```

Steps 8–10 are optional (pass `None` to skip if not yet wired).

## FastAPI usage

```python
background_tasks.add_task(
    orchestrator.process,
    user_id=user_id,
    question=question,
    ai_response=full_response,
    subject=profile.current_subject,
    grade=profile.grade,
    intent=classified_intent,
    duration_ms=elapsed_ms,
)
```

## Design invariant

`process()` is **always** called as a `BackgroundTask` — never awaited in the
request path. Zero latency added to the chat response.
