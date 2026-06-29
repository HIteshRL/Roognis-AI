# RAG Architecture — Phase 0.2

## Philosophy

> User → Academic Knowledge → Relevant Context → LLM → Grounded Answer

The LLM always receives retrieved institutional context before answering.
If no relevant context is found, the response is clearly marked as general knowledge.

## System Flow

```
User Message
    │
    ▼
ChatService.stream_response()
    │
    ├── RetrievalService.retrieve()
    │       ├── EmbeddingProvider.embed_query()   → query vector
    │       └── VectorStore.search()              → top-K chunks
    │
    ├── ContextValidationService.validate()       → filter low-quality chunks
    │
    ├── PromptAssemblyService.build_messages()
    │       ├── has_context=True  → rag_system template + context
    │       └── has_context=False → rag_no_context template
    │
    ├── LLMProvider.stream()                      → token stream
    │
    └── SSE → Frontend
              ├── meta  (conversation_id, rag sources)
              ├── chunk (content tokens)
              └── done  (message_id)
```

## SSE Meta Payload (Phase 0.2)

```json
{
  "type": "meta",
  "conversation_id": "uuid",
  "rag": {
    "has_context": true,
    "source_count": 3,
    "sources": [
      {"title": "Algorithms Chapter 1", "score": 0.85},
      {"title": "Data Structures", "score": 0.72}
    ]
  }
}
```

## Fallback Behaviour

| Situation | Response |
|-----------|----------|
| Context found (score ≥ threshold) | `rag_system` template with injected chunks |
| No context found | `rag_no_context` template — LLM answers from training data with disclaimer |
| RAG disabled (`RETRIEVAL_ENABLED=false`) | `default_system` template — Phase 0.1 behaviour |
| Qdrant unreachable | Fails open to Phase 0.1 behaviour (logged as error) |

## Layer Responsibilities

| Service | Responsibility |
|---------|----------------|
| `RetrievalService` | Vector similarity search |
| `ContextValidationService` | Quality filtering (score, length) |
| `PromptAssemblyService` | Template injection — never manual string concat |
| `VectorService` | Index management |
| `ChatService` | Orchestration only — no RAG logic |
