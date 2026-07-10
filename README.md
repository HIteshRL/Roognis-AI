# Intent Engine

**Layer:** Pedagogical classification  
**Phase:** 0.5  
**Dependencies:** None — pure Python, zero I/O

## What it does

Classifies every student message into one of seven pedagogical intent categories
before the LLM sees it. The result shapes the system prompt (different directive
per intent) and is stored on the learning session for analytics.

## Intent categories

| Intent | Trigger |
|---|---|
| `correction_request` | Student disputes or corrects the AI |
| `test_prep` | Exam revision, mock questions, board prep |
| `clarification` | Wants re-explanation or simpler terms |
| `recall` | Short factual look-up (≤ 10 words) |
| `problem_solving` | Calculation or step-by-step task |
| `concept_explanation` | "Why", "how", "difference between" |
| `unknown` | Nothing matched — safe fallback |

## Usage

```python
from engine import IntentEngine

engine = IntentEngine()
intent = engine.classify("why does current flow from high to low potential?")
# → "concept_explanation"
```

## Design notes

- Rule-based (no LLM call) — adds **zero latency** to the request path
- Runs once per request; result is passed to both `ChatService` and
  `LearningOrchestrator` so nothing executes twice
- Misfires are harmless: a wrong intent directive rarely breaks the LLM response
- Stateless: `IntentEngine` holds no state, safe to instantiate per-request
