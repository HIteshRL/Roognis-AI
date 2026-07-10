"""
PDF ingest pipeline (LMS workflow).

Teacher uploads a .pdf -> it is stored on disk compartmentalised by
classroom/chapter, parsed (rag-standalone PDFParser), split into chunks, and the
chunks are written to the chapter's corpus in the DB. The document row moves
through a status workflow: processing -> ready | failed, so the UI can poll.
"""
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_RAG = _HERE.parent / "rag-standalone"
if str(_RAG) not in sys.path:
    sys.path.insert(0, str(_RAG))

from src.infrastructure.parsing.pdf_parser import PDFParser  # noqa: E402

import store  # noqa: E402
from providers import sentences  # noqa: E402

_UPLOADS = _HERE / "data" / "uploads"
_MIN_CHUNK_CHARS = 25
_MAX_CHUNKS = 1200  # safety cap per document


def _save(classroom_id: str, chapter_id: str, document_id: str, data: bytes) -> Path:
    folder = _UPLOADS / classroom_id / chapter_id
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{document_id}.pdf"
    path.write_bytes(data)
    return path


async def ingest_pdf(document_id: str, chapter_id: str, classroom_id: str,
                     data: bytes, filename: str) -> None:
    """Background task: parse -> chunk -> persist. Never raises (records failure)."""
    try:
        path = _save(classroom_id, chapter_id, document_id, data)
        parsed = await PDFParser().parse(str(path))
        # Dedupe repeated lines (PDF page headers/footers repeat on every page).
        seen: set[str] = set()
        chunks: list[str] = []
        for s in sentences(parsed.full_text):
            if len(s) < _MIN_CHUNK_CHARS:
                continue
            key = " ".join(s.lower().split())
            if key in seen:
                continue
            seen.add(key)
            chunks.append(s)
            if len(chunks) >= _MAX_CHUNKS:
                break
        if not chunks:
            store.fail_document(document_id, "No extractable text (scanned PDF — OCR not enabled).")
            return
        store.finalize_document(document_id, chapter_id, parsed.total_pages, chunks)
    except Exception as exc:  # pragma: no cover - defensive
        store.fail_document(document_id, f"{type(exc).__name__}: {exc}")
