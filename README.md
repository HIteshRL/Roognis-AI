# Learner Context Builder

**Layer:** LLM prompt personalisation  
**Phase:** 0.3  
**Dependencies:** `structlog`

## What it does

The single most important engine for AI personalisation. Before every LLM
call it assembles a multi-section Markdown block injected into the system
prompt that tells the LLM *exactly* how to teach this specific student.

## Output structure

```
## Learner Profile (use this to personalize every response)

### Identity
- Grade 10, studying Refraction of Light
- Subjects: Physics, Chemistry
- Confidence: 67% | Velocity: 4.2 pts/day (active)

### Learning Patterns
- Operates best at Apply level; struggles when asked to Analyze
- Tends toward procedural thinking — prefers step-by-step methods
- Engagement: 5-day streak, 1.3 sessions/day

### Knowledge State
- Strengths: Ohm's Law, Newton's Laws (mastered)
- Weaknesses: Snell's Law (score 32), Refraction index (score 18)
- Active misconception in Refraction: "light speeds up in denser medium" (high severity, 3 occurrences)

### Teaching History
- Snell's Law: explained 4x, 25% success — try a completely different approach

### How to Teach This Student
- Lead with worked examples before stating abstract rules
- Scaffold analysis questions with simpler sub-questions first
- Current question intent: The student wants to solve a problem — walk through the method step by step.
```

## Integration

```python
from engine import LearnerContextService

svc = LearnerContextService(profile_repo=..., mastery_repo=..., gap_repo=...,
                             concept_memory_svc=concept_memory_service)
context_block = await svc.build(user_id, current_intent="problem_solving")
# → str | None  (None if not enough data yet)
```

## Called by

`ChatService` on every request, immediately before building the LLM message list.
The output is prepended to the system prompt.
