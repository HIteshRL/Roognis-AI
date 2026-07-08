import json
from uuid import UUID

import structlog
from groq import AsyncGroq

from src.domain.entities.learning import ConceptNode, MasteryRecord
from src.domain.entities.quiz import (
    DEFAULT_RATING,
    DIFFICULTY_RATINGS,
    BankedQuestion,
    Quiz,
    QuizQuestion,
)
from src.domain.repositories.learning_repository import (
    AbstractConceptNodeRepository,
    AbstractMasteryRepository,
)
from src.domain.repositories.quiz_repository import AbstractQuestionBankRepository

logger = structlog.get_logger(__name__)

_SYSTEM_PROMPT = """You are an expert K-12 assessment creator. Generate quiz questions for the given concepts.

Return ONLY valid JSON with this structure:
{
  "questions": [
    {
      "concept_name": "<concept this question tests>",
      "question_text": "<clear, unambiguous question>",
      "question_type": "mcq",
      "options": ["A) ...", "B) ...", "C) ...", "D) ..."],
      "correct_answer": "A) ...",
      "explanation": "<why the correct answer is right and common mistakes>",
      "bloom_level": "<Remember|Understand|Apply|Analyze|Evaluate|Create>",
      "difficulty": "<low|medium|high>"
    }
  ]
}

Rules:
- Each question MUST have exactly 4 options for mcq
- correct_answer MUST be one of the options (exact match)
- explanation should help students learn, not just state the answer
- Vary bloom levels across questions when possible
- Match difficulty to student mastery: low mastery → easier questions
"""


def _difficulty_for_mastery(score: float) -> str:
    if score >= 70:
        return "high"
    if score >= 40:
        return "medium"
    return "low"


class QuizGenerationService:
    def __init__(
        self,
        groq_client: AsyncGroq,
        mastery_repo: AbstractMasteryRepository,
        concept_repo: AbstractConceptNodeRepository,
        bank_repo: AbstractQuestionBankRepository | None = None,
    ) -> None:
        self._groq = groq_client
        self._mastery = mastery_repo
        self._concepts = concept_repo
        self._bank = bank_repo

    async def generate(
        self,
        user_id: UUID,
        subject: str | None = None,
        chapter: str | None = None,
        concept_ids: list[UUID] | None = None,
        question_count: int = 5,
        difficulty: str = "adaptive",
    ) -> tuple[Quiz, list[QuizQuestion]]:
        concepts = await self._resolve_concepts(
            user_id, subject, chapter, concept_ids, question_count
        )

        if not concepts:
            logger.warning("no_concepts_for_quiz", user_id=str(user_id))
            quiz = Quiz(
                user_id=user_id,
                title=self._build_title(subject, chapter),
                subject=subject,
                chapter=chapter,
                difficulty=difficulty,
                question_count=0,
            )
            return quiz, []

        mastery_map = await self._get_mastery_map(user_id, concepts)

        quiz = Quiz(
            user_id=user_id,
            title=self._build_title(subject, chapter),
            subject=subject,
            chapter=chapter,
            difficulty=difficulty,
        )
        concept_id_map = {c.name.lower(): c.id for c in concepts}

        # 1) Reuse banked questions near the student's ability first.
        banked = await self._pull_from_bank(concepts, mastery_map, question_count)

        # 2) Generate only what the bank couldn't supply.
        remaining = question_count - len(banked)
        new_banked: list[BankedQuestion] = []
        if remaining > 0:
            concept_descriptions = self._build_concept_prompt(concepts, mastery_map, difficulty)
            raw_questions = await self._call_llm(concept_descriptions, remaining)
            new_banked = self._raw_to_banked(raw_questions, concept_id_map)
            # Persist newly-generated items so the next quiz can reuse them.
            if self._bank and new_banked:
                try:
                    new_banked = await self._bank.create_many(new_banked)
                except Exception as exc:
                    logger.warning("question_bank_persist_failed", error=str(exc))

        linked = self._bank is not None
        questions: list[QuizQuestion] = []
        for i, b in enumerate(banked):
            questions.append(self._banked_to_quiz_question(b, quiz.id, i, linked=True))
        for j, b in enumerate(new_banked):
            questions.append(
                self._banked_to_quiz_question(b, quiz.id, len(banked) + j, linked=linked)
            )
        quiz.question_count = len(questions)

        logger.info(
            "quiz_generated",
            user_id=str(user_id),
            concepts=len(concepts),
            questions=len(questions),
            reused=len(banked),
            generated=len(new_banked),
        )
        return quiz, questions

    async def _pull_from_bank(
        self,
        concepts: list[ConceptNode],
        mastery_map: dict[UUID, MasteryRecord],
        total: int,
    ) -> list[BankedQuestion]:
        """Fetch banked questions whose difficulty rating is closest to the
        student's per-concept ability θ (maximum-information selection)."""
        if not self._bank:
            return []
        per = max(1, total // max(1, len(concepts)))
        picked: list[BankedQuestion] = []
        seen: set[UUID] = set()
        for c in concepts:
            record = mastery_map.get(c.id)
            theta = record.ability_rating if record and record.ability_rating is not None else DEFAULT_RATING
            try:
                items = await self._bank.list_for_concept(c.id, near_rating=theta, limit=per)
            except Exception as exc:
                logger.warning("question_bank_read_failed", error=str(exc))
                continue
            for it in items:
                if it.id not in seen:
                    picked.append(it)
                    seen.add(it.id)
            if len(picked) >= total:
                break
        return picked[:total]

    @staticmethod
    def _raw_to_banked(
        raw_questions: list[dict], concept_id_map: dict[str, UUID]
    ) -> list[BankedQuestion]:
        banked: list[BankedQuestion] = []
        for q_data in raw_questions:
            cname = q_data.get("concept_name", "")
            diff = q_data.get("difficulty", "medium")
            banked.append(
                BankedQuestion(
                    concept_name=cname,
                    concept_id=concept_id_map.get(cname.lower()),
                    question_text=q_data.get("question_text", ""),
                    question_type=q_data.get("question_type", "mcq"),
                    options=q_data.get("options", []),
                    correct_answer=q_data.get("correct_answer", ""),
                    explanation=q_data.get("explanation", ""),
                    bloom_level=q_data.get("bloom_level", "Understand"),
                    difficulty=diff,
                    difficulty_rating=DIFFICULTY_RATINGS.get(diff, DEFAULT_RATING),
                )
            )
        return banked

    @staticmethod
    def _banked_to_quiz_question(
        b: BankedQuestion, quiz_id: UUID, position: int, linked: bool
    ) -> QuizQuestion:
        return QuizQuestion(
            quiz_id=quiz_id,
            concept_name=b.concept_name,
            concept_id=b.concept_id,
            question_text=b.question_text,
            question_type=b.question_type,
            options=b.options,
            correct_answer=b.correct_answer,
            explanation=b.explanation,
            bloom_level=b.bloom_level,
            difficulty=b.difficulty,
            position=position,
            bank_question_id=b.id if linked else None,
        )

    async def _resolve_concepts(
        self,
        user_id: UUID,
        subject: str | None,
        chapter: str | None,
        concept_ids: list[UUID] | None,
        limit: int,
    ) -> list[ConceptNode]:
        if concept_ids:
            nodes = []
            for cid in concept_ids[:limit]:
                node = await self._concepts.get_by_id(cid)
                if node:
                    nodes.append(node)
            return nodes

        if subject:
            nodes = await self._concepts.list_by_subject_grade(
                subject=subject, grade=""
            )
            if chapter:
                nodes = [n for n in nodes if n.chapter == chapter]
            mastery_records = await self._mastery.list_by_user(user_id)
            mastery_scores = {
                str(r.concept_id): r.score for r in mastery_records
            }
            nodes.sort(key=lambda n: mastery_scores.get(str(n.id), 0.0))
            return nodes[:limit]

        mastery_records = await self._mastery.list_by_user(user_id)
        weakest = sorted(mastery_records, key=lambda r: r.score)[:limit]
        nodes = []
        for record in weakest:
            node = await self._concepts.get_by_id(record.concept_id)
            if node:
                nodes.append(node)
        return nodes

    async def _get_mastery_map(
        self, user_id: UUID, concepts: list[ConceptNode]
    ) -> dict[UUID, MasteryRecord]:
        records = await self._mastery.list_by_user(user_id)
        return {r.concept_id: r for r in records}

    def _build_concept_prompt(
        self,
        concepts: list[ConceptNode],
        mastery_map: dict[UUID, MasteryRecord],
        difficulty: str,
    ) -> str:
        lines = []
        for c in concepts:
            record = mastery_map.get(c.id)
            score = record.score if record else 0.0
            diff = (
                _difficulty_for_mastery(score)
                if difficulty == "adaptive"
                else difficulty
            )
            ctx = f"- {c.name}"
            if c.subject:
                ctx += f" (subject: {c.subject}"
                if c.chapter:
                    ctx += f", chapter: {c.chapter}"
                ctx += ")"
            ctx += f" [target difficulty: {diff}, current mastery: {score:.0f}%]"
            lines.append(ctx)
        return "\n".join(lines)

    async def _call_llm(
        self, concept_descriptions: str, question_count: int
    ) -> list[dict]:
        user_content = (
            f"Generate {question_count} quiz questions for these concepts:\n\n"
            f"{concept_descriptions}"
        )

        try:
            response = await self._groq.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": user_content},
                ],
                temperature=0.6,
                max_tokens=3000,
                response_format={"type": "json_object"},
            )
            raw = response.choices[0].message.content or "{}"
            data = json.loads(raw)
            return data.get("questions", [])
        except Exception as exc:
            logger.warning("quiz_generation_llm_failed", error=str(exc))
            return []

    @staticmethod
    def _build_title(subject: str | None, chapter: str | None) -> str:
        if subject and chapter:
            return f"{subject} — {chapter} Quiz"
        if subject:
            return f"{subject} Quiz"
        return "Practice Quiz"
