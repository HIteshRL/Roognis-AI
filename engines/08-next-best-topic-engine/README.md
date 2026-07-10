# Next Best Topic Engine

**Layer:** Recommendation  
**Phase:** 0.3 (extended 0.5)  
**Dependencies:** `structlog`, `pydantic`

## What it does

Given a student's mastery state and enrolled subjects, recommends the best
concept(s) to study next. Filters to concepts where prerequisites are
sufficiently mastered (≥ 50% readiness), then ranks by:

1. Readiness score descending (more prereqs met = higher priority)
2. Current mastery score ascending (low score + high readiness = most urgent)

## Integration

```python
from engine import NextBestTopicEngine

engine = NextBestTopicEngine(graph=..., mastery_repo=..., profile_repo=...)
recs = await engine.recommend(user_id)
# → [RecommendationResponse(concept_name="Ohm's Law", readiness_score=1.0, ...), ...]
```

## Relationship to Learning Path Engine

- **NextBestTopicEngine** answers "what should I study next?" — a short,
  ranked list for the student's current session
- **LearningPathEngine** answers "what's the full route to concept X?" —
  a longer ordered sequence for curriculum planning
