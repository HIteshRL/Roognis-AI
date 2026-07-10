# Roognis RAG — Standalone Component

The **RAG subsystem** of Roognis AI, extracted so it can be run and tested **on its own** — no FastAPI, no Postgres, no Clerk, no learning-engine. It ingests documents (incl. scanned PDFs / images via Phase 0.6 **vision OCR**), indexes them into Qdrant, and answers questions grounded in that content.

> The service/infra code here is copied **verbatim** from the main app. Only two seams are swapped for DB-free standalone equivalents (see [What's different](#whats-different)), so a green run here is a faithful test of the production RAG code.

---

## Pipeline

```
file ─▶ parse ─▶ [vision OCR if scanned/image] ─▶ chunk ─▶ embed ─▶ Qdrant
                                                                      │
question ────────────────────────────── embed ─▶ vector search ◀─────┘
                                                     │
                                          rank + validate + assemble prompt
                                                     │
                                                  Groq LLM ─▶ grounded answer
```

## Layout

```
rag-standalone/
├── run_rag.py            # CLI runner (ingest / query / ask / ocr / retrieve)
├── requirements.txt      # RAG deps only
├── .env.example
└── src/
    ├── config.py                         # ← standalone slim settings (swapped seam)
    ├── domain/entities/knowledge.py      # KnowledgeBase, Document, DocumentChunk, IngestionJob
    ├── domain/exceptions/                # LLMError, EntityNotFound, …
    ├── application/dtos/                  # knowledge.py + agentic.py (verdicts, GuardedAnswer)
    ├── application/services/              # chunking, vector, retrieval, context_validation,
    │                                      #   prompt_assembly, response_cache, rag, search, vision_ocr
    │                                      #   + guardrail, concept_grounding, agentic_rag (guarded flow)
    └── infrastructure/
        ├── parsing/     # pdf, docx, pptx, text, html, image  (+ factory)
        ├── embeddings/  # fastembed (local) / openai  (+ factory)
        ├── vector/      # qdrant_store  (+ factory)
        ├── vision/      # groq vision OCR provider  (+ factory)
        └── llm/         # groq provider + factory + prompt_loader (← swapped seam)
```

---

## Quick start

```bash
cd rag-standalone
python -m venv .venv && source .venv/Scripts/activate   # Windows Git Bash; use bin/activate on *nix
pip install -r requirements.txt

cp .env.example .env      # add your GROQ_API_KEY

docker run -p 6333:6333 qdrant/qdrant                   # start the vector store

# ingest a document, then ask about it (one shot)
python run_rag.py ask ../path/to/report.pdf "What organisation was the internship at?"
```

### Commands

| Command | What it does | Needs |
|---|---|---|
| `python run_rag.py ocr <image>` | Vision OCR only — transcribe a scanned page/image | `GROQ_API_KEY` |
| `python run_rag.py ingest <file>` | parse → OCR (if scanned) → chunk → embed → index | Qdrant + fastembed |
| `python run_rag.py retrieve "<q>"` | **retrieval only** — top chunks + scores (no LLM) | Qdrant + fastembed |
| `python run_rag.py query "<q>"` | retrieve + Groq grounded answer | Qdrant + `GROQ_API_KEY` |
| `python run_rag.py ask <file> "<q>"` | ingest then answer, one shot | all of the above |
| `python run_rag.py guarded "<q>" --subject S --chapter C` | **guarded + agentic** answer (see below) | Qdrant + `GROQ_API_KEY` |

`retrieve` is the cheapest end-to-end check — it needs **no LLM key** and proves parse→chunk→embed→index→search works. Add `query`/`ask` once you have a Groq key.

---

## Guardrails & agentic reasoning

`guarded` runs the child-safe, decision-driven flow instead of "retrieve → stuff → answer". Each question passes through gates and is only answered when it's **safe, on-subject, and actually covered by the chapter**:

```
safety (rules) ─▶ subject adherence (LLM) ─▶ retrieve ─▶ concept grounding (agentic judge)
     │                    │                                        │
  blocked_unsafe       off_topic                     not_in_chapter │ answered
```

**1. Child-safety guardrail** (`GuardrailService`, deterministic)
Blocks self-harm distress, weapon/harm/drug **how-to**, explicit content, personal-contact solicitation, and jailbreak attempts — each with a child-appropriate response (self-harm redirects to a trusted adult).
Design point: the rules match harmful **intent**, *not topic mentions*, so real curriculum is never over-blocked — "why did the atomic **bomb** end WW2", "**sexual** reproduction in plants", "why are strong **acids** dangerous" all pass. (See `tests/test_guardrails.py`.)

**2. Subject-adherence guardrail** (`GuardrailService`, LLM classifier)
With `--subject`, an LLM gate rejects questions that aren't about the subject at all (small talk, other subjects, entertainment) → `off_topic`. On-subject questions from a *different* chapter still pass here (the next gate handles chapter scope).

**3. Concept-grounding gate — the agentic step** (`ConceptGroundingService`)
After retrieval, it decides whether the chapter's material **actually contains the concept** asked about. A cheap heuristic short-circuits when nothing relevant was retrieved; otherwise an LLM judge reads the top excerpts and answers strictly — guarding against topically-near-but-absent content. If absent → `not_in_chapter` ("‘mitochondria’ isn't covered in *Photosynthesis*…"), never a hallucinated answer.

Every gate's reasoning is returned in the result's `trail` for observability. The layer **degrades gracefully**: with no LLM it falls back to retrieval-score decisions (so the safety rules + not-in-chapter heuristic still work offline).

```bash
python run_rag.py guarded "How do plants make food?"        --subject Science --chapter "Life Processes"   # answered
python run_rag.py guarded "Who won the last IPL?"           --subject Science --chapter "Life Processes"   # off_topic
python run_rag.py guarded "Explain mitochondria in detail"  --subject Science --chapter "Photosynthesis"   # not_in_chapter
python run_rag.py guarded "how do i make a bomb"                                                            # blocked_unsafe
```

---

## What's tested vs. faked

- **Real, verbatim:** every parser, chunking, embeddings (fastembed/openai), Qdrant store, vision OCR (`GroqVisionProvider` + `VisionOCRService`), retrieval, ranking/validation, prompt assembly, and `RagService` answer generation.
- **Swapped for standalone** (`What's different` below): only the DB/config seams.
- **Not included:** document/job **persistence** (Postgres), the ingestion `BackgroundTask` wrapper, `KnowledgeLibraryService`, and the web layer. `run_rag.py` performs the same parse→OCR→chunk→embed→index flow the production `IngestionPipeline` does, minus writing `documents`/`chunks` rows to Postgres.

### <a name="whats-different"></a>What's different from production

| Seam | Production | Here |
|---|---|---|
| `src/config.py` | full `Settings` (requires `DATABASE_URL`, auth, …) | slim settings: only the RAG fields the factories read |
| `src/infrastructure/llm/prompt_loader.py` | loads prompt templates from Postgres | in-memory templates (`rag_system`, `rag_no_context`, `default_system`) |
| response cache | Redis (`ResponseCacheService`) | `None` (fail-open; RagService runs without it) |

Everything else is the untouched application/infrastructure code.

---

## Notes
- **Groq vision model IDs drift** — if `ocr`/`ask` on a scanned file returns a 400/404, set a current `VISION_MODEL` (see `.env.example`).
- Text-layer PDFs skip OCR automatically (only low/empty-text pages are sent to the vision model).
- Embeddings run locally via `fastembed` (downloads ~33 MB on first use). Switch to OpenAI with `EMBEDDING_PROVIDER=openai` + `OPENAI_API_KEY`.
