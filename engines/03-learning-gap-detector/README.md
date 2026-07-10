# Learning Gap Detector

**Layer:** Misconception tracking  
**Phase:** 0.3  
**Dependencies:** `structlog`, `pydantic`

## What it does

Converts misconceptions surfaced by the Concept Extraction Engine into
persistent `LearningGap` records. Gaps escalate in severity the more they
recur, and are auto-resolved when the student reaches mastery.

## Severity escalation

| Occurrences | Severity | Confidence |
|---|---|---|
| 1 | medium | medium |
| 2 | medium | medium |
| 3–4 | high | high |
| 5+ | critical | high |

## Integration

```python
from engine import LearningGapDetector

detector = LearningGapDetector(gap_repo=..., concept_repo=...)
gaps = await detector.process_extraction(user_id, extraction, subject="Chemistry")
```

## Called by

`LearningOrchestrator` in the post-response pipeline.
Auto-resolution happens in the orchestrator after mastery scores are updated.
