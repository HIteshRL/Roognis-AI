"""
ConceptGroundingService — the agentic decision gate.

After retrieval, before answering, this decides: does the chapter's material
ACTUALLY contain the concept the student is asking about? This is what makes the
tutor reason about the question instead of blindly answering from loosely-related
chunks.

Two-step decision:
  1. Cheap heuristic — if nothing was retrieved above a floor score, the concept
     is not in the chapter. No LLM call needed.
  2. LLM judge — reads the top chapter excerpts and the question and decides,
     strictly, whether the concept is genuinely covered (guards against retrieval
     returning topically-near but conceptually-absent content).

Degrades gracefully: with no LLM, it uses the retrieval score alone.
"""
import structlog

from src.application.dtos.agentic import GroundingVerdict
from src.application.services.llm_json import llm_json
from src.infrastructure.llm.base import AbstractLLMProvider

logger = structlog.get_logger(__name__)


class ConceptGroundingService:
    def __init__(
        self,
        llm: AbstractLLMProvider | None = None,
        model: str = "llama-3.1-8b-instant",
        min_top_score: float = 0.30,
        max_excerpts: int = 4,
    ) -> None:
        self._llm = llm
        self._model = model
        self._min_top_score = min_top_score
        self._max_excerpts = max_excerpts

    async def assess(self, question: str, chunks: list, chapter: str | None = None) -> GroundingVerdict:
        # Step 1 — heuristic short-circuit.
        top = chunks[0].score if chunks else 0.0
        if not chunks or top < self._min_top_score:
            return GroundingVerdict(
                concept_present=False,
                confidence=0.9,
                decision="NOT_IN_CHAPTER",
                reason=f"No chapter content retrieved above the relevance floor (top score {top:.2f}).",
                missing=question,
            )

        # No LLM available → trust retrieval score.
        if not self._llm:
            return GroundingVerdict(
                concept_present=True,
                confidence=round(float(top), 3),
                decision="ANSWER",
                reason="Relevant chapter content retrieved (score-based, no judge).",
            )

        # Step 2 — LLM judge over the actual excerpts.
        excerpts = "\n\n".join(
            f"[score {c.score:.2f}] {c.content[:500].strip()}" for c in chunks[: self._max_excerpts]
        )
        system = (
            "You verify whether chapter excerpts genuinely contain the concept a student is "
            "asking about. Be STRICT: only mark it present if the excerpts actually cover the "
            "concept well enough to answer. Topically-related but different concepts count as "
            "NOT present. Reply with JSON only."
        )
        user = (
            f"Chapter: {chapter or 'N/A'}\n"
            f'Student question: "{question}"\n\n'
            f"Chapter excerpts:\n{excerpts}\n\n"
            'Return JSON: {"concept_present": true|false, "confidence": 0..1, '
            '"missing": "the concept the student asked about, if absent", "reason": "short"}'
        )
        try:
            data = await llm_json(self._llm, self._model, system, user, max_tokens=250)
        except Exception as exc:
            logger.warning("grounding_llm_failed", error=str(exc))
            # Fail-open to the score heuristic rather than refuse a valid question.
            return GroundingVerdict(True, round(float(top), 3), "ANSWER", "Judge unavailable; score-based.")

        present = bool(data.get("concept_present", True))
        return GroundingVerdict(
            concept_present=present,
            confidence=float(data.get("confidence", 0.5) or 0.5),
            decision="ANSWER" if present else "NOT_IN_CHAPTER",
            reason=str(data.get("reason", "")),
            missing=(None if present else str(data.get("missing") or question)),
        )
