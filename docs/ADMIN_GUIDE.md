# Admin Guide — Phase 0.2

## Granting Admin Access

Set `is_admin=true` directly in PostgreSQL:

```sql
UPDATE users SET is_admin = true WHERE email = 'admin@example.com';
```

Admin status is checked on every admin API call — no token refresh required.

## Admin Workflow

### 1. Create a Knowledge Base

Navigate to `/admin/library` → "New knowledge base" → fill name, institution, subject.

Or via API:
```bash
POST /api/v1/library
Authorization: Bearer <token>
{
  "name": "Computer Science Year 1",
  "institution": "MIT",
  "subject": "Algorithms"
}
```

### 2. Upload Documents

Navigate to `/admin/upload` → select knowledge base → drag & drop files.

Or via API:
```bash
POST /api/v1/documents/upload/{kb_id}
Authorization: Bearer <token>
Content-Type: multipart/form-data
file: <binary>
```

### 3. Monitor Ingestion

Each upload creates an `IngestionJob`. Poll:
```bash
GET /api/v1/documents/{kb_id}/{doc_id}/status
```

Job status progression: `queued → parsing → chunking → embedding → indexing → done`

### 4. Verify Chunks

```bash
GET /api/v1/documents/{kb_id}/{doc_id}/chunks
```

Returns all chunks with content, token count, and page numbers.

### 5. Test Search

Navigate to `/admin/search` or:
```bash
POST /api/v1/search
{
  "query": "What is binary search?",
  "knowledge_base_id": "optional-uuid",
  "top_k": 5,
  "score_threshold": 0.35
}
```

### 6. Reindex a Document

If chunking config changed or embeddings were reset:
```bash
POST /api/v1/documents/{kb_id}/{doc_id}/reindex
```

### 7. Delete a Document

Removes file from storage, chunks from PostgreSQL, and vectors from Qdrant:
```bash
DELETE /api/v1/documents/{kb_id}/{doc_id}
```

## Vector Stats

```bash
GET /api/v1/admin/vector/stats
```

Returns: collection name, vectors_count, points_count, status.

## Environment Tuning

| Variable | Effect |
|----------|--------|
| `CHUNK_SIZE` | Larger = more context per chunk, fewer chunks |
| `CHUNK_OVERLAP` | Larger = better boundary coverage, more storage |
| `RETRIEVAL_TOP_K` | More results = richer context, more tokens |
| `RETRIEVAL_SCORE_THRESHOLD` | Higher = stricter matching, fewer hallucinations |
