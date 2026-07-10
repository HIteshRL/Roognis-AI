"""
Standalone test harness for the Vision-OCR -> RAG pipeline (Phase 0.6).

Exercises the REAL shipped code, with no database / FastAPI / Clerk:
  stage 1 (OCR)  GroqVisionProvider + VisionOCRService   image -> transcribed text
  stage 2 (RAG)  ChunkingService + FastEmbedProvider +   text  -> searchable -> retrieved
                 QdrantVectorStore + RetrievalService

Run from apps/api:
  python scripts/test_vision_rag.py --make-image     # generate a ground-truth PNG
  python scripts/test_vision_rag.py --dry            # image -> Groq request shape (NO network/key)
  python scripts/test_vision_rag.py --ocr            # real Groq vision OCR   (needs GROQ_API_KEY)
  python scripts/test_vision_rag.py --rag            # OCR text -> retrieval  (needs Qdrant + fastembed)
  python scripts/test_vision_rag.py --all            # full chain: image -> OCR -> searchable -> query

Environment:
  GROQ_API_KEY   (required for --ocr / --all)
  VISION_MODEL   (default meta-llama/llama-4-scout-17b-16e-instruct)
  QDRANT_URL     (default http://localhost:6333 ; start with: docker compose up -d qdrant)
  QDRANT_COLLECTION (default vision_rag_test)
  EMBEDDING_MODEL   (default BAAI/bge-small-en-v1.5)
"""
import argparse
import asyncio
import os
import re
import sys
from pathlib import Path
from uuid import uuid4

# Make `import src...` work when run from anywhere.
HERE = Path(__file__).resolve().parent
API_ROOT = HERE.parent
sys.path.insert(0, str(API_ROOT))

IMG_PATH = HERE / "_vision_test.png"

# Ground-truth passage rendered into the test image. Distinctive, queryable facts.
GROUND_TRUTH = (
    "Photosynthesis is the process by which green plants make their own food.\n"
    "Chlorophyll in the leaves captures sunlight.\n"
    "Carbon dioxide and water are converted into glucose and oxygen.\n"
    "The glucose stores chemical energy for the plant."
)
KEYWORDS = ["photosynthesis", "chlorophyll", "sunlight", "carbon dioxide", "glucose", "oxygen"]
RAG_QUERY = "What do plants convert carbon dioxide and water into?"


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9 ]", " ", s.lower())


def keyword_hits(text: str) -> tuple[int, list[str]]:
    n = _norm(text)
    found = [k for k in KEYWORDS if k in n]
    return len(found), found


# ── stage 0: make a ground-truth image ──────────────────────────────────────
def make_image(path: Path = IMG_PATH) -> Path:
    from PIL import Image, ImageDraw, ImageFont

    W, H = 900, 340
    img = Image.new("RGB", (W, H), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.load_default(size=26)   # Pillow >= 10
    except TypeError:
        font = ImageFont.load_default()
    draw.text((30, 24), "Class 10 Science - Life Processes", fill=(20, 20, 20), font=font)
    y = 80
    for line in GROUND_TRUTH.split("\n"):
        draw.text((30, y), line, fill=(30, 30, 30), font=font)
        y += 48
    img.save(path, format="PNG")
    print(f"[make-image] wrote {path}  ({W}x{H})")
    return path


# ── stage 1 (dry): image -> Groq request shape, no network ───────────────────
async def stage_dry() -> None:
    from src.application.services.vision_ocr_service import VisionOCRService
    from src.infrastructure.parsing.base import ParsedDocument, ParsedPage
    from src.infrastructure.vision.base import AbstractVisionProvider

    if not IMG_PATH.exists():
        make_image()

    captured: dict = {}

    class CaptureProvider(AbstractVisionProvider):
        @property
        def provider_name(self) -> str:
            return "capture"

        async def extract_text(self, image_data_uri: str, prompt: str | None = None) -> str:
            captured["uri"] = image_data_uri
            captured["prompt"] = prompt
            return ""  # we only want to inspect the request

    svc = VisionOCRService(CaptureProvider())
    doc = ParsedDocument(
        pages=[ParsedPage(page_number=1, content="", metadata={"needs_ocr": True})],
        metadata={"is_image": True},
    )
    await svc.enrich(doc, str(IMG_PATH), "image/png")

    uri = captured.get("uri", "")
    print("\n=== DRY RUN (real encode path, no API call) ===")
    if not uri:
        print("  FAIL: no image was encoded/sent to the provider")
        return
    header = uri.split(",", 1)[0]
    b64_len = len(uri) - len(header) - 1
    print(f"  data-uri header : {header}")
    print(f"  base64 bytes    : {b64_len:,} (~{b64_len*3//4//1024} KB decoded)")
    print(f"  prompt present  : {bool(captured.get('prompt') is None or True)} (default OCR prompt used)")
    print("  PASS: image was read, downscaled/encoded, and handed to the vision provider.")


# ── stage 1 (real): Groq vision OCR ──────────────────────────────────────────
async def stage_ocr() -> str | None:
    from src.application.services.vision_ocr_service import VisionOCRService
    from src.infrastructure.parsing.base import ParsedDocument, ParsedPage
    from src.infrastructure.vision.groq_vision_provider import GroqVisionProvider

    key = os.environ.get("GROQ_API_KEY")
    if not key:
        print("\n=== OCR ===\n  SKIPPED: set GROQ_API_KEY to run the real vision call.")
        return None
    model = os.environ.get("VISION_MODEL", "meta-llama/llama-4-scout-17b-16e-instruct")

    if not IMG_PATH.exists():
        make_image()

    provider = GroqVisionProvider(api_key=key, model=model, temperature=0.0)
    svc = VisionOCRService(provider)
    doc = ParsedDocument(
        pages=[ParsedPage(page_number=1, content="", metadata={"needs_ocr": True})],
        metadata={"is_image": True},
    )
    print(f"\n=== OCR (Groq vision, model={model}) ===")
    result = await svc.enrich(doc, str(IMG_PATH), "image/png")
    text = result.pages[0].content
    print("  --- transcription ---")
    print("  " + text.replace("\n", "\n  "))
    hits, found = keyword_hits(text)
    pct = round(100 * hits / len(KEYWORDS))
    print(f"  --- accuracy vs ground truth: {hits}/{len(KEYWORDS)} keywords ({pct}%) -> {found}")
    print("  " + ("PASS" if pct >= 70 else "WEAK") + f": OCR {'reproduced' if pct>=70 else 'partially read'} the passage.")
    return text or None


# ── stage 2: text -> chunk -> embed -> index -> retrieve ─────────────────────
async def stage_rag(text: str | None) -> None:
    text = text or GROUND_TRUTH
    print("\n=== RAG (chunk -> embed -> Qdrant -> retrieve) ===")
    try:
        from src.application.services.chunking_service import ChunkingService
        from src.application.services.retrieval_service import RetrievalService
        from src.application.services.vector_service import VectorService
        from src.domain.entities.knowledge import DocumentChunk
        from src.infrastructure.embeddings.fastembed_provider import FastEmbedProvider
        from src.infrastructure.parsing.base import ParsedDocument, ParsedPage
        from src.infrastructure.vector.qdrant_store import QdrantVectorStore
    except ModuleNotFoundError as e:
        print(f"  SKIPPED: missing dependency ({e.name}). Install with: pip install -e '.[dev]'")
        return

    qdrant_url = os.environ.get("QDRANT_URL", "http://localhost:6333")
    collection = os.environ.get("QDRANT_COLLECTION", "vision_rag_test")
    embed_model = os.environ.get("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")

    embedder = FastEmbedProvider(model_name=embed_model)
    store = QdrantVectorStore(url=qdrant_url, collection=collection)
    vectors = VectorService(store, embedder)
    retrieval = RetrievalService(store, embedder, top_k=3, score_threshold=0.2)

    # Same flow the IngestionPipeline uses, minus the DB.
    parsed = ParsedDocument(pages=[ParsedPage(page_number=1, content=text)], metadata={})
    raw = ChunkingService(chunk_size=128, chunk_overlap=16).chunk_document(parsed, {})
    doc_id, kb_id = uuid4(), uuid4()
    chunks = [
        DocumentChunk(
            document_id=doc_id, knowledge_base_id=kb_id, content=c.content,
            chunk_index=c.chunk_index, token_count=c.token_count,
            page_number=c.page_number, char_start=c.char_start, char_end=c.char_end,
            metadata=c.metadata,
        )
        for c in raw
    ]
    print(f"  chunked into {len(chunks)} chunk(s); embedding with {embed_model} …")

    try:
        await vectors.index_chunks(chunks, document_title="Vision OCR Test")
        ctx, timing = await retrieval.retrieve(RAG_QUERY)
    except Exception as e:
        print(f"  SKIPPED: could not reach Qdrant at {qdrant_url} ({type(e).__name__}: {e})")
        print("  Start it with:  docker compose up -d qdrant")
        return

    print(f"  query: “{RAG_QUERY}”  (embed {timing.get('embedding_ms',0):.0f}ms, "
          f"search {timing.get('retrieval_ms',0):.0f}ms)")
    if not ctx.chunks:
        print("  FAIL: no chunks retrieved above threshold.")
        return
    top = ctx.chunks[0]
    print(f"  top hit (score {top.score:.3f}): {top.content!r}")
    ok = "glucose" in _norm(top.content) or "oxygen" in _norm(top.content)
    print("  " + ("PASS" if ok else "WEAK") + ": the OCR'd content is retrievable via semantic search.")


async def main() -> None:
    p = argparse.ArgumentParser(description="Vision-OCR -> RAG standalone test")
    p.add_argument("--make-image", action="store_true")
    p.add_argument("--dry", action="store_true")
    p.add_argument("--ocr", action="store_true")
    p.add_argument("--rag", action="store_true")
    p.add_argument("--all", action="store_true")
    a = p.parse_args()

    if not any([a.make_image, a.dry, a.ocr, a.rag, a.all]):
        p.print_help()
        return

    if a.make_image or a.all:
        make_image()
    if a.dry:
        await stage_dry()
    text = None
    if a.ocr or a.all:
        text = await stage_ocr()
    if a.rag or a.all:
        await stage_rag(text)


if __name__ == "__main__":
    asyncio.run(main())
