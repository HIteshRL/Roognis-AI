# Roognis AI — Engine Library

Each subfolder is a self-contained, extractable engine module.
Every folder has its own `engine.py`, `domain.py` (interfaces + entities),
`requirements.txt`, and `README.md`.

Each engine is also published as an independent orphan branch on GitHub
(`engine/<name>`) so it can be cloned or vendored independently.

## Engines

| # | Folder | Branch | What it does |
|---|---|---|---|
| 01 | `01-intent-engine` | `engine/intent-engine` | Zero-latency pedagogical intent classification (rule-based) |
| 02 | `02-mastery-engine` | `engine/mastery-engine` | Per-concept mastery score updates (EMA + Bloom gains) |
| 03 | `03-learning-gap-detector` | `engine/learning-gap-detector` | Misconception → persistent gap escalation |
| 04 | `04-learner-behavior-analyzer` | `engine/learner-behavior-analyzer` | Behavioral signals from session history |
| 05 | `05-learning-velocity-engine` | `engine/learning-velocity-engine` | Velocity (pts/day) + Ebbinghaus retention risk |
| 06 | `06-skill-graph-engine` | `engine/skill-graph-engine` | Bloom → competency domain skill profile |
| 07 | `07-learning-path-engine` | `engine/learning-path-engine` | Topological learning path + frontier concepts |
| 08 | `08-next-best-topic-engine` | `engine/next-best-topic-engine` | Ranked "what to study next" recommendations |
| 09 | `09-concept-memory-engine` | `engine/concept-memory-engine` | Per-concept teaching history (approach + success rate) |
| 10 | `10-concept-extraction-engine` | `engine/concept-extraction-engine` | LLM extraction of concepts + Bloom + misconceptions |
| 11 | `11-learner-context-builder` | `engine/learner-context-builder` | Assembles personalised LLM system prompt block |
| 12 | `12-learning-orchestrator` | `engine/learning-orchestrator` | Post-response background pipeline coordinator |

## RAG engines (separate repo)

The guardrailed agentic RAG engines live in `../rag-standalone` and are
published on the `rag-standalone` orphan branch.

| Engine | What it does |
|---|---|
| `AgenticRagService` | 5-gate pipeline: safety → subject → retrieve → grounding → answer |
| `GuardrailService` | Intent-based child-safety + subject-relevance gate |
| `ConceptGroundingService` | Scores how well retrieved context covers the question |
| `ContextValidationService` | Validates retrieved context quality |
