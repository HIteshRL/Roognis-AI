"""
AgenticRagService — guarded, decision-driven RAG.

Instead of "retrieve → stuff → answer", it routes each question through gates and
only answers when it's safe, on-subject, AND the concept exists in the chapter:

    safety (rules) ─▶ subject adherence (LLM) ─▶ retrieve ─▶ validate
                                                              │
                                       concept grounding (agentic judge)
                                              │
                        ┌── not present ──▶ "not covered in this chapter"
                        └── present ──────▶ grounded answer (LLM)

Every gate's reasoning is returned in `trail` so the decision is observable/testable.
Built on the existing services — retrieval, context validation, prompt assembly,
LLM — nothing in the base pipeline is modified.
"""
import structlog

from src.application.dtos.agentic import GuardedAnswer, RelevanceVerdict
from src.application.services.concept_grounding_service import ConceptGroundingService
from src.application.services.context_validation_service import ContextValidationService
from src.application.services.guardrail_service import GuardrailService
from src.application.services.prompt_assembly_service import PromptAssemblyService
from src.application.services.retrieval_service import RetrievalService
from src.infrastructure.llm.base import AbstractLLMProvider, LLMConfig

logger = structlog.get_logger(__name__)


class AgenticRagService:
    def __init__(
        self,
        guardrail: GuardrailService,
        grounding: ConceptGroundingService,
        retrieval: RetrievalService,
        prompt_assembly: PromptAssemblyService,
        llm: AbstractLLMProvider,
        llm_model: str,
        context_validation: ContextValidationService | None = None,
    ) -> None:
        self._guardrail = guardrail
        self._grounding = grounding
        self._retrieval = retrieval
        self._prompt_assembly = prompt_assembly
        self._llm = llm
        self._model = llm_model
        self._validation = context_validation

    async def ask(
        self,
        question: str,
        subject: str | None = None,
        chapter: str | None = None,
        knowledge_base_id: str | None = None,
    ) -> GuardedAnswer:
        # ── Gate 1: safety (deterministic) ───────────────────────────────────
        safety = self._guardrail.check_safety(question)
        if safety.blocked:
            return GuardedAnswer(
                decision="blocked_unsafe",
                message=safety.message,
                trail={"gate": "safety", "category": safety.category},
            )

        # ── Gate 2: subject adherence ────────────────────────────────────────
        relevance: RelevanceVerdict = await self._guardrail.check_subject_relevance(
            question, subject, chapter
        )
        if not relevance.on_topic:
            return GuardedAnswer(
                decision="off_topic",
                message=(
                    f"Let's stay on {subject}! That looks like a different topic. "
                    f"Ask me about {chapter or 'this chapter'} instead."
                ),
                trail={"gate": "subject", "reason": relevance.reason},
            )

        # ── Retrieve chapter context ─────────────────────────────────────────
        ctx, timing = await self._retrieval.retrieve(question, knowledge_base_id=knowledge_base_id)
        if self._validation:
            ctx = self._validation.validate(ctx)
        sources = [
            {"title": c.document_title, "score": round(c.score, 3)} for c in ctx.chunks
        ]

        # ── Gate 3: concept grounding (agentic) ──────────────────────────────
        grounding = await self._grounding.assess(question, ctx.chunks, chapter)
        if not grounding.concept_present:
            concept = grounding.missing or "that topic"
            return GuardedAnswer(
                decision="not_in_chapter",
                message=(
                    f"Good question — but “{concept}” doesn't appear to be covered in "
                    f"{chapter or 'this chapter'}. Try a topic from this chapter, or ask your teacher."
                ),
                sources=sources,
                trail={"gate": "grounding", "reason": grounding.reason,
                       "confidence": grounding.confidence},
            )

        # ── Answer, grounded in the retrieved chapter context ────────────────
        messages = await self._prompt_assembly.build_messages(
            user_message=question, history=[], context=ctx
        )
        try:
            resp = await self._llm.complete(
                messages, LLMConfig(model=self._model, temperature=0.2, stream=False)
            )
        except Exception as exc:
            logger.error("agentic_answer_failed", error=str(exc))
            return GuardedAnswer(decision="error", message="The tutor is unavailable right now.",
                                 sources=sources, trail={"gate": "answer", "error": str(exc)})

        return GuardedAnswer(
            decision="answered",
            answer=resp.content,
            sources=sources,
            trail={
                "relevance": relevance.reason,
                "grounding": grounding.reason,
                "grounding_confidence": grounding.confidence,
                "retrieval_ms": round(timing.get("retrieval_ms", 0)),
            },
        )
