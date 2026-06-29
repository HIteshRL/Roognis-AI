# Vector Database — Phase 0.2

## Provider Abstraction

```
AbstractVectorStore
    ↓ implemented by
QdrantVectorStore (default)
    ↓ selected by
factory.get_vector_store()
    ↓ consumed by
VectorService (application layer)
```

To switch providers: implement `AbstractVectorStore`, register in `factory.py`. Zero changes to application services.

## Qdrant Configuration

```env
VECTOR_PROVIDER=qdrant
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=         # empty for local, set for Qdrant Cloud
QDRANT_COLLECTION=roognis_knowledge
```

Docker Compose starts Qdrant on port 6333 (HTTP) and 6334 (gRPC).

## Collection Schema

Single collection `roognis_knowledge` with COSINE distance.

Each point payload:
```json
{
  "chunk_id": "uuid",
  "document_id": "uuid",
  "knowledge_base_id": "uuid",
  "document_title": "string",
  "content": "string",
  "chunk_index": 0,
  "page_number": 3,
  "token_count": 512
}
```

## Search Parameters

```env
RETRIEVAL_TOP_K=5               # max results per query
RETRIEVAL_SCORE_THRESHOLD=0.35  # minimum cosine similarity (0–1)
RETRIEVAL_ENABLED=true
```

## Adding a New Provider

1. Implement `AbstractVectorStore` in `src/infrastructure/vector/`
2. Register it in `factory.py`
3. Set `VECTOR_PROVIDER=<name>` in `.env`

Supported in future phases: Pinecone, Weaviate, Chroma, Milvus.
