# Learner Behavior Analyzer

**Layer:** Behavioral intelligence  
**Phase:** 0.3  
**Dependencies:** `structlog`

## What it does

Mines a student's last 30 days of sessions and computes `BehavioralSignals` —
a structured descriptor of *how* this student learns, not just *what* they know.
These signals are stored as JSONB on the student profile and injected into the
LLM system prompt so every response is stylistically adapted to the learner.

## Signals computed

| Signal | How |
|---|---|
| `preferred_bloom_level` | Most frequent Bloom level in sessions |
| `struggle_bloom_level` | Bloom level with most misconceptions |
| `avg_session_duration_ms` | Mean duration of sessions with duration > 0 |
| `sessions_per_day` | Frequency over the analysis window |
| `question_complexity_trend` | `rising / stable / declining` from Bloom rank delta |
| `dominant_subject` | Most-studied subject |
| `total_misconceptions` | Count of unresolved learning gaps |
| `engagement_streak` | Consecutive study days |
| `strengths` | Top 5 concepts with score ≥ 85 |
| `recent_topics` | Last 5 unique primary concepts |
| `response_pattern` | `procedural / conceptual / mixed` |

## Integration

```python
from engine import LearnerBehaviorService

svc = LearnerBehaviorService(session_repo=..., mastery_repo=..., gap_repo=...)
signals = await svc.compute(user_id)
# → BehavioralSignals(preferred_bloom_level='Apply', response_pattern='procedural', ...)
```

## Called by

`LearningOrchestrator` after every session. Output stored via `StudentProfileService.update_behavioral_signals()`.
