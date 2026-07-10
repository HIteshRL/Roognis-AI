# Skill Graph Engine

**Layer:** Competency derivation  
**Phase:** 0.5  
**Dependencies:** None — pure Python, zero I/O

## What it does

Converts mastery records + session history into a human-readable skill profile.
Maps Bloom taxonomy levels to named competency domains (e.g., "Apply" → "Problem Solving",
"Analyze" → "Critical Analysis"). Never persisted — recomputed fresh on every `/student/skills` call.

## Bloom → Skill mapping

| Bloom level | Skills |
|---|---|
| Remember | Knowledge Recall, Memorization |
| Understand | Conceptual Understanding, Reading Comprehension |
| Apply | Problem Solving, Procedural Execution |
| Analyze | Critical Analysis, Pattern Recognition |
| Evaluate | Critical Thinking, Judgment & Evaluation |
| Create | Synthesis, Creative Thinking |

## Usage

```python
from engine import SkillGraphService

svc = SkillGraphService()
profile = svc.build_student_skill_profile(mastery_records, sessions)
# → {"Problem Solving": 74.2, "Critical Analysis": 61.0, ...}

top = svc.top_skills(profile, n=5)
dist = svc.categorize_bloom_distribution(sessions)
```

## Design note

Skill profile is **derived, not stored** — avoids a skills table and keeps
data always current. Proficiency = weighted average mastery score across all
concepts exercised at that Bloom level.
