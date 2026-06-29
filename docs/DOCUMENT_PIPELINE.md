# Document Pipeline — Phase 0.2

## Upload → Index Flow

```
1. Admin uploads file via POST /api/v1/documents/upload/{kb_id}
2. DocumentService validates file type + size
3. File saved to LocalFileStorage (./uploads/{kb_id}/{doc_id}.ext)
4. Document record created (status=pending)
5. IngestionJob record created (status=queued)
6. FastAPI BackgroundTask starts IngestionPipeline.run()

IngestionPipeline.run():
  parsing   (10%) → AbstractDocumentParser extracts text + page metadata
  chunking  (30%) → ChunkingService splits into TextChunks
  embedding (50%) → AbstractEmbeddingProvider generates vectors
  indexing  (80%) → VectorService upserts to Qdrant + persists chunks to DB
  done      (100%) → Document.status=ready, IngestionJob.status=done
```

## Supported Formats

| Extension | Parser | Notes |
|-----------|--------|-------|
| `.pdf` | `PDFParser` (pypdf) | Text extraction per page |
| `.docx` | `DocxParser` (python-docx) | Paragraphs joined |
| `.pptx` | `PptxParser` (python-pptx) | Per-slide text |
| `.txt`, `.csv` | `TextParser` | Raw text |
| `.md`, `.markdown` | `MarkdownParser` | HTML→text via beautifulsoup4 |
| `.html`, `.htm` | `HtmlParser` | HTML→text via beautifulsoup4 |

## Chunking Configuration

```env
CHUNK_SIZE=512          # tokens per chunk
CHUNK_OVERLAP=64        # overlap between adjacent chunks
CHUNK_STRATEGY=fixed    # fixed | semantic | sliding
```

Token counting uses `tiktoken` with `cl100k_base` encoding.

## Chunk Metadata

Every chunk carries:
```json
{
  "document_id": "uuid",
  "knowledge_base_id": "uuid",
  "document_title": "filename or title",
  "chunk_index": 0,
  "page_number": 3,
  "token_count": 512,
  "institution": "...",
  "subject": "..."
}
```

## Reindexing

`POST /api/v1/documents/{kb_id}/{doc_id}/reindex`

1. Deletes existing Qdrant vectors for the document
2. Deletes existing chunk records from PostgreSQL
3. Restarts full ingestion pipeline from the stored file
