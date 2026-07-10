# Learning Velocity Engine

**Layer:** Temporal learning analytics  
**Phase:** 0.4  
**Dependencies:** `structlog`

## What it does

Produces two temporal signals that quantify how fast a student is learning
and which concepts are at risk of being forgotten.

### 1. Learning Velocity
Bloom-weighted mastery points earned per day over the trailing 7-day window.
Misconceptions apply a 5-point penalty per session.

```
velocity = Σ max(0, BLOOM_GAINS[bloom_level] - 5·has_misconception) / window_days
```

### 2. Retention Risk (Ebbinghaus-style forgetting curve)
Scores each mastered/developing concept by how likely it is to have decayed.
Stronger mastery has a longer half-life; the longer since last reinforcement,
the higher the risk score.

```
risk = 1 - exp(-days_since / (14 * (0.5 + mastery/100)))
```
Concepts with `risk >= 0.4` surface as "at risk" in the analytics dashboard.

## Integration

```python
from engine import LearningVelocityService

svc = LearningVelocityService(session_repo=..., mastery_repo=...)
velocity = await svc.compute_velocity(user_id)               # → float (pts/day)
risks    = await svc.compute_retention_risks(user_id)        # → list[RetentionRisk]
```

## Called by

`LearningOrchestrator` (velocity) and `LearningAnalyticsService` (retention risks).
