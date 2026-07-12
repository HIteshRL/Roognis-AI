"""
Wires the SQLite-backed LMS to rag-standalone's guarded, agentic RAG.

Seeds the DB from the ghost curriculum on first run, then serves the real
AgenticRagService flow (safety -> subject -> retrieve -> concept-grounding ->
answer) with DB-backed retrieval (seed + uploaded-PDF chunks) and conversation
logging so the teacher can review what students ask.
"""
import os
import sys
from pathlib import Path

_RAG = Path(__file__).resolve().parent.parent / "rag-standalone"
if str(_RAG) not in sys.path:
    sys.path.insert(0, str(_RAG))

from src.application.services.agentic_rag_service import AgenticRagService  # noqa: E402
from src.application.services.concept_grounding_service import ConceptGroundingService  # noqa: E402
from src.application.services.prompt_assembly_service import PromptAssemblyService  # noqa: E402
from src.config import get_settings  # noqa: E402
from src.infrastructure.llm.prompt_loader import PromptLoader  # noqa: E402

import curriculum  # noqa: E402
import db  # noqa: E402
import store  # noqa: E402
from providers import (  # noqa: E402
    CorpusGuardrail,
    DbRetrieval,
    OfflineTutorProvider,
    is_generic_followup,
    sentences,
    tokens,
)

_SUBJECT_FLOOR = 0.34
_CHAPTER_FLOOR = 0.25

# ── Boot: schema + (optional) demo seed ──────────────────────────────────────
# The teacher builds real classes and uploads real material, so the demo subject
# classrooms are NOT seeded by default. Set ROOGNIS_SEED_DEMO=1 to restore them.
db.init_db()
if os.getenv("ROOGNIS_SEED_DEMO") == "1":
    db.seed_from_curriculum(curriculum.SUBJECTS, sentences)

_settings = get_settings()
ONLINE = bool(_settings.groq_api_key)
MODE = "Groq LLM" if ONLINE else "offline (extractive)"

if ONLINE:
    from src.infrastructure.llm.groq_provider import GroqProvider
    _answer_llm = GroqProvider(api_key=_settings.groq_api_key)
    _gate_llm = GroqProvider(api_key=_settings.groq_api_key)
else:
    _answer_llm = OfflineTutorProvider()
    _gate_llm = None

# Subject-relevance corpus (classroom name -> vocabulary). Rebuilt after uploads.
_subject_corpus: dict[str, set[str]] = {}


def rebuild_corpus() -> None:
    _subject_corpus.clear()
    for room in store.list_classrooms():
        vocab: set[str] = set()
        for ch in store.list_chapters(room["id"]):
            for chunk in store.get_chapter_chunks(ch["id"]):
                vocab |= tokens(chunk)
        _subject_corpus[room["name"]] = vocab


rebuild_corpus()

_agentic = AgenticRagService(
    guardrail=CorpusGuardrail(_subject_corpus, subject_floor=_SUBJECT_FLOOR),
    grounding=ConceptGroundingService(llm=_gate_llm, min_top_score=_CHAPTER_FLOOR),
    retrieval=DbRetrieval(),
    prompt_assembly=PromptAssemblyService(PromptLoader()),
    llm=_answer_llm,
    llm_model=_settings.groq_default_model,
    context_validation=None,
)


async def ask(question: str, classroom_id: str, chapter_id: str,
              student_id: str, conversation_id: str | None) -> dict:
    room = store.get_classroom(classroom_id)
    chapter = store.get_chapter(chapter_id)

    # A conversational follow-up ("how does it work?") carries no keywords, so it
    # would retrieve nothing and be wrongly refused. Anchor it to the current
    # chapter so it retrieves the right content and answers in context.
    ask_question = question
    if chapter and is_generic_followup(question):
        ask_question = f"{chapter['title']}: {question}"

    res = await _agentic.ask(
        ask_question,
        subject=room["name"] if room else None,
        chapter=chapter["title"] if chapter else None,
        knowledge_base_id=chapter_id,
    )

    # Log the exchange so the teacher can review it.
    if not conversation_id:
        title = (question[:48] + "…") if len(question) > 48 else question
        conversation_id = store.create_conversation(student_id, classroom_id, chapter_id, title)
    store.add_message(conversation_id, "user", question)
    store.add_message(conversation_id, "assistant", res.answer or res.message or "", res.decision)

    return {
        "decision": res.decision, "answer": res.answer, "message": res.message,
        "sources": res.sources, "trail": res.trail, "mode": MODE,
        "conversation_id": conversation_id,
    }
