# Concept Extraction Engine

**Layer:** LLM-powered metadata extraction  
**Phase:** 0.3  
**Dependencies:** `groq`, `structlog`, `pydantic`  
**LLM:** Groq `llama3-8b-8192` (fast, cheap)

## What it does

Sends each student Q+A pair to a small LLM and extracts structured learning
metadata. This is the only engine in the pipeline that makes an LLM call —
all other engines consume the result.

## Output schema

```json
{
  "primary_concept": "Ohm's Law",
  "secondary_concepts": ["Electric current", "Resistance"],
  "skills": ["Problem Solving", "Procedural Execution"],
  "bloom_level": "Apply",
  "difficulty": "medium",
  "misconceptions": []
}
```

## Integration

```python
from groq import AsyncGroq
from engine import ConceptExtractionService

svc = ConceptExtractionService(groq_client=AsyncGroq(api_key="gsk_..."))
result = await svc.extract(question, ai_response, subject="Physics", grade="10")
```

## Fail-open design

On any error (API timeout, malformed JSON, validation failure), the engine
returns a safe default rather than raising. The learning pipeline **must never
fail** because the extraction engine did — the chat response was already sent.

## Called by

`LearningOrchestrator` first, before any other engine in the pipeline.
All other engines receive this result as input.
