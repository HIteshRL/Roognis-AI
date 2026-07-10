# Mastery Engine

**Layer:** Learning analytics  
**Phase:** 0.3  
**Dependencies:** `structlog`, `pydantic`

## What it does

Updates a student's per-concept mastery score (0–100) after every interaction.
Uses an EMA-style smoothed gain model so a single great session can't spike
a concept to 100, and a single mistake doesn't tank a strong score.

## Scoring model

```
gain        = BLOOM_GAINS[bloom_level]   # 3 (Remember) → 15 (Create)
penalty     = 15 if misconception else 0
session_pts = max(0, gain - penalty)
new_score   = 0.7 * old_score + 0.3 * (old_score + session_pts)
new_score   = clamp(new_score, 0, 100)
```

## Mastery labels

| Score | Label |
|---|---|
| ≥ 85 | `mastered` |
| ≥ 60 | `developing` |
| ≥ 30 | `emerging` |
| < 30 | `not_started` |

## Integration

Implement `AbstractMasteryRepository` and `AbstractConceptNodeRepository`
from `domain.py`, then inject into `MasteryEngine`:

```python
from engine import MasteryEngine

engine = MasteryEngine(mastery_repo=..., concept_repo=...)
await engine.update_from_extraction(user_id, extraction, subject="Physics", grade="10")
```

## Called by

`LearningOrchestrator` as part of the post-response background pipeline.
