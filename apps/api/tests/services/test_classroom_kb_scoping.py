"""Teacher content bridge — retrieval must stay bounded to a class KB.

The cascade broadens subject→grade→…, but when a student's classroom knowledge
base is in scope it must NEVER fall through to a global (unfiltered) search —
that would leak one classroom's material into another's tutor.
"""
from src.application.services.retrieval_service import RetrievalService


def test_cascade_without_kb_ends_unscoped():
    cascade = RetrievalService._build_cascade("Mathematics", "Fractions", "8", None)
    names = [name for name, _ in cascade]
    assert names[-1] == "unscoped"
    assert cascade[-1][1] is None  # global fallback allowed for open RAG


def test_cascade_with_kb_stays_bounded():
    kb = "kb-123"
    cascade = RetrievalService._build_cascade("Mathematics", "Fractions", "8", kb)

    # No level may drop the KB filter — the broadest is KB-only, never None.
    assert all(payload is not None for _, payload in cascade)
    assert all(
        payload.get("knowledge_base_id") == kb for _, payload in cascade
    )
    assert cascade[-1] == ("kb", {"knowledge_base_id": kb})


def test_cascade_with_kb_but_no_curriculum_scope():
    kb = "kb-xyz"
    cascade = RetrievalService._build_cascade(None, None, None, kb)
    assert cascade == [("kb", {"knowledge_base_id": kb})]
