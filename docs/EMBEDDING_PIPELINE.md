# Embedding Pipeline — Phase 0.2

## Provider Abstraction

```
AbstractEmbeddingProvider
    ↓ implemented by
FastEmbedProvider (default — local ONNX, no API key)
OpenAIEmbeddingProvider (optional)
    ↓ selected by
factory.get_embedding_provider()
```

## Default: fastembed

```env
EMBEDDING_PROVIDER=fastembed
EMBEDDING_MODEL=BAAI/bge-small-en-v1.5
EMBEDDING_DIMENSION=384
```

- ONNX runtime — no GPU, no PyTorch required
- Model downloads automatically on first use (~32 MB)
- Production-quality multilingual embeddings

## Alternative: OpenAI

```env
EMBEDDING_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSION=1536
```

## Batch Indexing

`VectorService.index_chunks()` processes in batches of 32 to avoid memory spikes and respect API rate limits. Each batch is upserted to Qdrant immediately — no intermediate storage.

## Adding a New Provider

1. Implement `AbstractEmbeddingProvider` in `src/infrastructure/embeddings/`
2. Register it in `factory.py`
3. Set `EMBEDDING_PROVIDER=<name>` in `.env`
4. Set `EMBEDDING_DIMENSION` to match the new model's output size

**Critical:** `EMBEDDING_DIMENSION` must match the Qdrant collection dimension. If switching providers on an existing collection, delete the collection first (or create a new one with a different name).
