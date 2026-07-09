"""
Standalone RAG runner — drives the extracted RAG components end-to-end.

  python run_rag.py ocr    <image>                    # vision OCR only (needs GROQ_API_KEY)
  python run_rag.py ingest <file>                     # parse -> OCR -> chunk -> embed -> index (Qdrant)
  python run_rag.py query  "<question>"               # retrieve + LLM answer over what's indexed
  python run_rag.py ask    <file>  "<question>"       # ingest then answer, one shot
  python run_rag.py retrieve "<question>"             # retrieval ONLY (no LLM / no key needed)

Needs a running Qdrant for ingest/query/retrieve:  docker run -p 6333:6333 qdrant/qdrant
Config comes from env / .env (see .env.example).
"""
import argparse
import asyncio
import sys
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.config import get_settings  # noqa: E402


def _build():
    """Assemble the real RAG services (incl. the guarded/agentic layer)."""
    from src.application.services.agentic_rag_service import AgenticRagService
    from src.application.services.concept_grounding_service import ConceptGroundingService
    from src.application.services.context_validation_service import ContextValidationService
    from src.application.services.guardrail_service import GuardrailService
    from src.application.services.prompt_assembly_service import PromptAssemblyService
    from src.application.services.rag_service import RagService
    from src.application.services.retrieval_service import RetrievalService
    from src.application.services.vector_service import VectorService
    from src.application.services.vision_ocr_service import VisionOCRService
    from src.infrastructure.embeddings.factory import get_embedding_provider
    from src.infrastructure.llm.factory import get_llm_provider
    from src.infrastructure.llm.prompt_loader import PromptLoader
    from src.infrastructure.vector.factory import get_vector_store
    from src.infrastructure.vision.factory import get_vision_provider

    s = get_settings()
    embedder = get_embedding_provider()
    store = get_vector_store()
    llm = get_llm_provider()
    vectors = VectorService(store, embedder)
    retrieval = RetrievalService(store, embedder, s.retrieval_top_k, s.retrieval_score_threshold)
    prompt_assembly = PromptAssemblyService(PromptLoader())
    validation = ContextValidationService(s.retrieval_score_threshold)
    ocr = VisionOCRService(
        get_vision_provider(), enabled=s.ocr_enabled,
        min_chars_per_page=s.ocr_min_chars_per_page, max_pages=s.ocr_max_pages,
        max_image_dimension=s.ocr_max_image_dimension, image_format=s.ocr_image_format,
    )
    rag = RagService(
        retrieval_svc=retrieval, prompt_assembly_svc=prompt_assembly,
        context_validation_svc=validation, llm_provider=llm,
        llm_model=s.groq_default_model, response_cache_svc=None,
    )
    # Guarded, agentic flow layered on top of the same building blocks.
    _extract_model = "llama-3.1-8b-instant"  # cheap model for gate decisions
    guardrail = GuardrailService(llm=llm, model=_extract_model)
    grounding = ConceptGroundingService(
        llm=llm, model=_extract_model, min_top_score=s.retrieval_score_threshold
    )
    agentic = AgenticRagService(
        guardrail=guardrail, grounding=grounding, retrieval=retrieval,
        prompt_assembly=prompt_assembly, llm=llm, llm_model=s.groq_default_model,
        context_validation=validation,
    )
    return s, vectors, retrieval, ocr, rag, agentic


async def do_ocr(path: str) -> str | None:
    from src.infrastructure.parsing.base import ParsedDocument, ParsedPage
    _, _, _, ocr, _, _ = _build()
    doc = ParsedDocument(
        pages=[ParsedPage(page_number=1, content="", metadata={"needs_ocr": True})],
        metadata={"is_image": True},
    )
    out = await ocr.enrich(doc, path, "image/png")
    text = out.pages[0].content
    print("=== OCR result ===")
    print(text or "(nothing transcribed)")
    return text or None


async def do_ingest(path: str) -> int:
    from src.application.services.chunking_service import ChunkingService
    from src.domain.entities.knowledge import DocumentChunk
    from src.infrastructure.parsing.factory import get_parser

    s, vectors, _, ocr, _, _ = _build()
    parser = get_parser(path)
    parsed = await parser.parse(path)
    parsed = await ocr.enrich(parsed, path, None)          # Phase 0.6 vision OCR (scanned/image docs)
    raw = ChunkingService(s.chunk_size, s.chunk_overlap, s.chunk_strategy).chunk_document(parsed, {})

    doc_id, kb_id = uuid4(), uuid4()
    chunks = [
        DocumentChunk(
            document_id=doc_id, knowledge_base_id=kb_id, content=c.content,
            chunk_index=c.chunk_index, token_count=c.token_count, page_number=c.page_number,
            char_start=c.char_start, char_end=c.char_end, metadata=c.metadata,
        )
        for c in raw
    ]
    await vectors.index_chunks(chunks, document_title=Path(path).name)
    ocr_note = " (vision OCR applied)" if parsed.metadata.get("ocr_applied") else ""
    print(f"=== ingested {Path(path).name}: {parsed.total_pages} pages -> "
          f"{len(chunks)} chunks indexed into '{s.qdrant_collection}'{ocr_note} ===")
    return len(chunks)


async def do_retrieve(question: str) -> None:
    _, _, retrieval, _, _, _ = _build()
    ctx, timing = await retrieval.retrieve(question)
    print(f"=== retrieval for: {question!r}  (embed {timing.get('embedding_ms',0):.0f}ms, "
          f"search {timing.get('retrieval_ms',0):.0f}ms) ===")
    if not ctx.chunks:
        print("  no chunks above threshold.")
        return
    for i, c in enumerate(ctx.chunks, 1):
        print(f"  [{i}] score={c.score:.3f}  {c.content[:160].strip()!r}")


async def do_query(question: str) -> None:
    from src.application.dtos.knowledge import CurriculumFilter, RagQueryRequest
    _, _, _, _, rag, _ = _build()
    req = RagQueryRequest(query=question, curriculum=CurriculumFilter(), include_chunks=True)
    resp = await rag.query(req)
    print(f"=== answer for: {question!r} ===")
    print(resp.answer)
    obs = resp.observability
    print(f"\n[chunks={getattr(obs,'chunk_count','?')} "
          f"retrieval={getattr(obs,'retrieval_ms',0):.0f}ms llm={getattr(obs,'llm_ms',0):.0f}ms]")


async def do_guarded(question: str, subject: str | None, chapter: str | None) -> None:
    _, _, _, _, _, agentic = _build()
    res = await agentic.ask(question, subject=subject, chapter=chapter)
    icon = {"answered": "✅", "blocked_unsafe": "🛑", "off_topic": "↪️",
            "not_in_chapter": "📕", "error": "⚠️"}.get(res.decision, "•")
    print(f"=== {icon} decision: {res.decision} ===")
    if res.answer:
        print(res.answer)
    if res.message:
        print(res.message)
    if res.sources:
        print("  sources:", ", ".join(f"{s['title']}({s['score']})" for s in res.sources[:3]))
    if res.trail:
        print("  trail:", res.trail)


async def main() -> None:
    p = argparse.ArgumentParser(description="Standalone RAG runner")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("ocr").add_argument("path")
    sub.add_parser("ingest").add_argument("path")
    sub.add_parser("retrieve").add_argument("question")
    sub.add_parser("query").add_argument("question")
    a_ask = sub.add_parser("ask")
    a_ask.add_argument("path")
    a_ask.add_argument("question")
    a_guard = sub.add_parser("guarded", help="safety + subject + concept-grounding, then answer")
    a_guard.add_argument("question")
    a_guard.add_argument("--subject", default=None)
    a_guard.add_argument("--chapter", default=None)
    a = p.parse_args()

    if a.cmd == "ocr":
        await do_ocr(a.path)
    elif a.cmd == "ingest":
        await do_ingest(a.path)
    elif a.cmd == "retrieve":
        await do_retrieve(a.question)
    elif a.cmd == "query":
        await do_query(a.question)
    elif a.cmd == "ask":
        await do_ingest(a.path)
        await do_query(a.question)
    elif a.cmd == "guarded":
        await do_guarded(a.question, a.subject, a.chapter)


if __name__ == "__main__":
    asyncio.run(main())
