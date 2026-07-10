# Learning Path Engine

**Layer:** Curriculum navigation  
**Phase:** 0.5  
**Dependencies:** `structlog`, `pydantic`

## What it does

Combines the knowledge graph topology with the student's mastery state to
answer three questions:

1. **path_to_concept** — What do I need to learn *before* concept X?
2. **get_frontier** — What am I *ready* to learn right now?
3. **curriculum_coverage** — How much of each subject have I mastered?

## Topological ordering

Uses **Kahn's algorithm** (implemented in `AbstractKnowledgeGraph.learning_order`)
over the prerequisite graph. Handles disconnected subgraphs and cycles by
appending unprocessed nodes at the end (fail-open).

## Readiness score

`readiness_for(concept_id, mastery_map)` returns 0–1:
- 1.0 = all prerequisites mastered (score ≥ 85)
- 0.5 = half the prerequisites met
- 0.0 = no prerequisites met

Concepts with readiness < 0.5 are excluded from the frontier.

## Integration

Implement `AbstractKnowledgeGraph` (see `domain.py`), then:

```python
from engine import LearningPathService

svc = LearningPathService(graph=..., mastery_repo=..., profile_repo=...)
frontier = await svc.get_frontier(user_id)
path = await svc.path_to_concept(user_id, target_concept_id)
```
