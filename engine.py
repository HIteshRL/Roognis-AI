"""
Concept Extraction Engine — Roognis AI

Uses an LLM (Groq Llama 3.1 8B) to extract structured learning metadata
from a student Q+A pair. Called once per session in the background pipeline.

Extracts:
  primary_concept      — the main concept discussed (noun phrase, max 5 words)
  secondary_concepts   — up to 4 supporting concepts
  skills               — cognitive/procedural skills exercised
  bloom_level          — highest Bloom level demonstrated
  difficulty           — low | medium | high
  misconceptions       — factual errors visible in the student's question
"""
import json

import structlog
from groq import AsyncGroq

from domain import ConceptExtractionResult

logger = structlog.get_logger(__name__)

_SYSTEM_PROMPT = """You are a curriculum analysis assistant. Given a student question and the AI's answer, extract the learning concepts involved.

Return ONLY valid JSON with this exact structure:
{
  "primary_concept": "<the main concept being discussed>",
  "secondary_concepts": ["<related concept 1>", "<related concept 2>"],
  "skills": ["<skill 1>", "<skill 2>"],
  "bloom_level": "<one of: Remember, Understand, Apply, Analyze, Evaluate, Create>",
  "difficulty": "<one of: low, medium, high>",
  "misconceptions": ["<misconception found in the question>"]
}

Rules:
- primary_concept: the single most important concept (noun phrase, max 5 words)
- secondary_concepts: up to 4 supporting concepts
- skills: cognitive or procedural skills exercised
- bloom_level: the highest Bloom's taxonomy level demonstrated
- difficulty: overall difficulty of the concept for the stated grade level
- misconceptions: ONLY include if the student's question reveals a clear factual error; else empty list
"""


class ConceptExtractionService:
    def __init__(self, groq_client: AsyncGroq) -> None:
        self._groq = groq_client

    async def extract(
        self,
        question: str,
        ai_response: str,
        subject: str | None = None,
        grade: str | None = None,
    ) -> ConceptExtractionResult:
        context_hint = ""
        if subject:
            context_hint += f"Subject: {subject}\n"
        if grade:
            context_hint += f"Grade: {grade}\n"

        user_content = (
            f"{context_hint}"
            f"Student question: {question}\n\n"
            f"AI answer: {ai_response[:2000]}"
        )

        try:
            response = await self._groq.chat.completions.create(
                model="llama3-8b-8192",
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": user_content},
                ],
                temperature=0.1,
                max_tokens=512,
                response_format={"type": "json_object"},
            )
            raw = response.choices[0].message.content or "{}"
            data = json.loads(raw)
            return ConceptExtractionResult(**data)
        except Exception as exc:
            logger.warning("concept_extraction_failed", error=str(exc))
            return ConceptExtractionResult(
                primary_concept=subject or "General Concept",
                bloom_level="Understand",
                difficulty="medium",
            )
