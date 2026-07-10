"""Run a real document through the ingestion pipeline's parse + chunk stages.

Usage: python scripts/ingest_file.py "<path-to-file>" "<out-text-path>"
Uses the shipped PDFParser + ChunkingService (no DB / embeddings / Qdrant).
Writes the extracted text to out-path and prints ingestion stats.
"""
import asyncio
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

_MIN_CHARS = 20  # matches settings.ocr_min_chars_per_page


async def main(src: str, out: str) -> None:
    from src.application.services.chunking_service import ChunkingService
    from src.infrastructure.parsing.pdf_parser import PDFParser

    # Use PDFParser directly (the factory eagerly imports docx/pptx parsers).
    parser = PDFParser()
    parsed = await parser.parse(src)
    text = parsed.full_text

    low_text_pages = sum(1 for p in parsed.pages if len(p.content.strip()) < _MIN_CHARS)
    chunks = ChunkingService(chunk_size=512, chunk_overlap=64).chunk_document(parsed, {})

    Path(out).write_text(text, encoding="utf-8")

    print(f"parser              : {type(parser).__name__}")
    print(f"pages               : {parsed.total_pages}")
    print(f"extracted chars     : {len(text):,}")
    print(f"low/empty-text pages: {low_text_pages}  "
          f"({'would trigger vision OCR' if low_text_pages else 'has a text layer — no OCR needed'})")
    print(f"chunks (512/64)     : {len(chunks)}")
    print(f"text written to     : {out}")
    print("----- preview (first 600 chars) -----")
    print(text[:600].strip())


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1], sys.argv[2]))
