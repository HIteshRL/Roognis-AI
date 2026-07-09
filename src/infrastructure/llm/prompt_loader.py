"""
Standalone (in-memory) PromptLoader for the RAG component.

The production app loads prompt templates from PostgreSQL. For a DB-free
standalone RAG, this drop-in exposes the SAME interface (`await get(name)`)
but serves the RAG templates from constants. Same class name + method
signature, so the RAG services import it unchanged.
"""
import structlog

logger = structlog.get_logger(__name__)

_TEMPLATES: dict[str, str] = {
    "default_system": (
        "You are Roognis, an intelligent AI learning assistant. "
        "You help learners understand concepts clearly and accurately. "
        "Be concise, correct, and encouraging."
    ),
    # Used when retrieval found context. {context} is replaced with the
    # formatted, ranked chunks before the call.
    "rag_system": (
        "You are Roognis, an AI tutor. Answer the user's question using ONLY the "
        "curriculum context provided below. Do not use outside knowledge. If the "
        "answer is not contained in the context, reply exactly: "
        "\"I cannot find this information in the provided materials.\"\n\n"
        "Cite the relevant ideas naturally and stay concise.\n\n"
        "--- CURRICULUM CONTEXT ---\n{context}\n--- END CONTEXT ---"
    ),
    # Used when retrieval found nothing above threshold.
    "rag_no_context": (
        "You are Roognis, an AI tutor. No curriculum context was retrieved for "
        "this question. Tell the learner you couldn't find relevant material in "
        "the provided documents, and invite them to rephrase or pick another topic. "
        "Do not fabricate an answer."
    ),
}


class PromptLoader:
    """In-memory template store. Constructed with no arguments."""

    def __init__(self) -> None:
        self._cache = dict(_TEMPLATES)

    async def get(self, name: str) -> str:
        tpl = self._cache.get(name, "")
        if not tpl:
            logger.warning("prompt_template_missing", name=name)
        return tpl

    def invalidate(self, name: str) -> None:
        self._cache.pop(name, None)
