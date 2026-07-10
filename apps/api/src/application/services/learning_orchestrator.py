"""
Ties the full learning pipeline together.
Called as a FastAPI BackgroundTask after each chat/RAG response is streamed.
Never raises — failures are logged and swallowed so they never affect the user response.
"""
from uuid import UUID

import structlog

from src.application.dtos.learning import ConceptExtractionResult
from src.application.services.concept_extraction_service import ConceptExtractionService
from src.application.services.concept_memory_service import ConceptMemoryService
from src.application.services.evidence_collector import EvidenceCollector
from src.application.services.learner_behavior_service import LearnerBehaviorService
from src.application.services.learning_gap_detector import LearningGapDetector
from src.application.services.learning_velocity_service import LearningVelocityService
from src.application.services.mastery_engine import MasteryEngine
from src.application.services.preference_inference_engine import PreferenceInferenceEngine
from src.application.services.session_memory_service import SessionMemoryService
from src.application.services.student_profile_service import StudentProfileService
from src.domain.repositories.learning_repository import AbstractConceptNodeRepository

logger = structlog.get_logger(__name__)


class LearningOrchestrator:
    def __init__(
        self,
        extractor: ConceptExtractionService,
        profile_svc: StudentProfileService,
        session_svc: SessionMemoryService,
        mastery_engine: MasteryEngine,
        gap_detector: LearningGapDetector,
        velocity_svc: LearningVelocityService | None = None,
        behavior_svc: LearnerBehaviorService | None = None,
        concept_memory_svc: ConceptMemoryService | None = None,
        evidence_collector: EvidenceCollector | None = None,
        preference_engine: PreferenceInferenceEngine | None = None,
        concept_repo: AbstractConceptNodeRepository | None = None,
    ) -> None:
        self._extractor = extractor
        self._profiles = profile_svc
        self._sessions = session_svc
        self._mastery = mastery_engine
        self._gaps = gap_detector
        self._velocity = velocity_svc
        self._behavior = behavior_svc
        self._concept_memory = concept_memory_svc
        self._evidence = evidence_collector
        self._preferences = preference_engine
        self._concepts = concept_repo

    async def process(
        self,
        user_id: UUID,
        question: str,
        ai_response: str,
        conversation_id: UUID | None = None,
        subject: str | None = None,
        chapter: str | None = None,
        grade: str | None = None,
        retrieved_context: str | None = None,
        intent: str = "unknown",
        token_count: int = 0,
        duration_ms: int = 0,
    ) -> None:
        try:
            extraction: ConceptExtractionResult = await self._extractor.extract(
                question=question,
                ai_response=ai_response,
                subject=subject,
                grade=grade,
            )

            # Ensure profile exists and is touched
            await self._profiles.get_or_create(user_id)
            await self._profiles.touch(user_id)

            # Record the learning session (includes classified intent)
            await self._sessions.record(
                user_id=user_id,
                question=question,
                ai_response=ai_response,
                extraction=extraction,
                conversation_id=conversation_id,
                subject=subject,
                chapter=chapter,
                grade=grade,
                retrieved_context=retrieved_context,
                intent=intent,
                token_count=token_count,
                duration_ms=duration_ms,
            )

            # Update mastery for all concepts touched
            await self._mastery.update_from_extraction(
                user_id=user_id,
                extraction=extraction,
                subject=subject,
                grade=grade,
                chapter=chapter,
            )

            # Detect and escalate learning gaps from misconceptions
            await self._gaps.process_extraction(
                user_id=user_id,
                extraction=extraction,
                subject=subject,
                grade=grade,
                chapter=chapter,
            )

            # Auto-resolve gaps for concepts that reached mastery
            await self._auto_resolve_gaps(user_id)

            # Refresh confidence score from current average mastery
            avg = await self._mastery.average(user_id)
            await self._profiles.refresh_confidence(user_id, avg)

            # Refresh learning velocity trend (points/day over trailing window)
            if self._velocity:
                velocity = await self._velocity.compute_velocity(user_id)
                await self._profiles.update_velocity(user_id, velocity)

            # Recompute behavioral signals from session history
            if self._behavior:
                signals = await self._behavior.compute(user_id)
                await self._profiles.update_behavioral_signals(user_id, signals)

            # Update per-concept teaching memory
            if self._concept_memory:
                await self._concept_memory.record_from_extraction(
                    user_id=user_id,
                    extraction=extraction,
                    subject=subject,
                    grade=grade,
                    chapter=chapter,
                )

            # Learner Intelligence: log evidence from this chat turn + refine
            # inferred preferences. Isolated so it never disturbs the pipeline above.
            await self._record_learner_intelligence(
                user_id=user_id,
                extraction=extraction,
                subject=subject,
                grade=grade,
                chapter=chapter,
                intent=intent,
            )

            logger.info(
                "learning_pipeline_complete",
                user_id=str(user_id),
                concept=extraction.primary_concept,
                bloom=extraction.bloom_level,
                misconceptions=len(extraction.misconceptions),
            )
        except Exception as exc:
            logger.error(
                "learning_pipeline_error",
                user_id=str(user_id),
                error=str(exc),
                exc_info=True,
            )

    async def _record_learner_intelligence(
        self,
        user_id: UUID,
        extraction: ConceptExtractionResult,
        subject: str | None,
        grade: str | None,
        chapter: str | None,
        intent: str,
    ) -> None:
        """Emit chat-turn evidence and refine inferred preferences. Fail-open.

        Chat is *weak* evidence: a demonstrated misconception is real negative
        evidence, but an explanation the learner merely received is neutral — we
        log it (signal ``unknown``, zero polarity) without asserting mastery, so
        it never inflates assessment confidence. Mastery/gap updates are owned by
        the steps above; we deliberately do not re-apply them here.
        """
        had_misconception = len(extraction.misconceptions) > 0

        if self._preferences:
            try:
                await self._preferences.infer_from_interaction(
                    user_id=user_id,
                    intent=intent,
                    bloom_level=extraction.bloom_level,
                    had_misconception=had_misconception,
                )
            except Exception as exc:
                logger.warning("preference_inference_failed", error=str(exc))

        if self._evidence and extraction.primary_concept:
            try:
                concept_id = None
                concept_name = extraction.primary_concept
                if self._concepts:
                    node = await self._concepts.get_or_create(
                        concept_name, subject, grade, chapter
                    )
                    concept_id = node.id
                signal = "misconception" if had_misconception else "unknown"
                confidence = 0.0
                if concept_id is not None:
                    confidence = await self._evidence.concept_confidence(user_id, concept_id)
                await self._evidence.record(
                    user_id=user_id,
                    signal=signal,
                    concept_id=concept_id,
                    concept_name=concept_name,
                    objective="verify_confidence",
                    source="chat",
                    weight=0.5 if had_misconception else 0.3,
                    bloom_level=extraction.bloom_level,
                    intent=intent,
                    confidence_before=confidence,
                    confidence_after=confidence,
                    detail=extraction.misconceptions[0] if had_misconception else "",
                )
            except Exception as exc:
                logger.warning("chat_evidence_record_failed", error=str(exc))

    async def _auto_resolve_gaps(self, user_id: UUID) -> None:
        mastery_records = await self._mastery.get_all(user_id)
        mastered_concepts = {r.concept_id for r in mastery_records if r.score >= 85}
        if not mastered_concepts:
            return

        active_gaps = await self._gaps.list_gaps(user_id, include_resolved=False)
        for gap in active_gaps:
            if gap.concept_id in mastered_concepts:
                await self._gaps.resolve(gap.id)
                logger.info(
                    "gap_auto_resolved",
                    user_id=str(user_id),
                    concept=gap.concept_name,
                    score=next(
                        (r.score for r in mastery_records if r.concept_id == gap.concept_id), 0
                    ),
                )
