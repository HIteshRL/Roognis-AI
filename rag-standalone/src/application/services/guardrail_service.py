"""
GuardrailService — child-usage safety + subject adherence.

Two layers, run before the tutor ever answers:

  1. Safety (deterministic rules). High-PRECISION intent patterns — they target
     harmful *requests/how-to* and personal distress, NOT mere topic mentions.
     This is deliberate: a K-12 curriculum legitimately covers wars (history),
     reproduction (biology), acids/explosives (chemistry). Blocking on those
     words would break real learning, so we only block harmful intent, self-harm
     distress, explicit content, personal-contact solicitation, and jailbreaks.

  2. Subject adherence (LLM classifier). Given the subject (and chapter), decides
     whether the question is even about this subject. Off-topic questions (small
     talk, other subjects, entertainment) are redirected, not answered.

The chapter-level "does this concept exist here" check is a separate, later gate
(ConceptGroundingService) — this class only guards safety and subject scope.
"""
import re

import structlog

from src.application.dtos.agentic import RelevanceVerdict, SafetyVerdict
from src.application.services.llm_json import llm_json
from src.infrastructure.llm.base import AbstractLLMProvider

logger = structlog.get_logger(__name__)

_SUPPORT = (
    "It sounds like you might be going through something really hard. I'm just a "
    "study helper, but please talk to a trusted adult — a parent, teacher, or school "
    "counsellor — who can support you right now. You matter. 💙"
)
_REDIRECT = "Let's keep things safe and get back to learning — what topic are you studying?"

# (category, compiled pattern, child-facing message). Order matters: self-harm first.
_SAFETY_RULES: list[tuple[str, re.Pattern[str], str]] = [
    (
        "self_harm",
        re.compile(
            r"\b(i|i'?m|im)\s+(want|wanna|going|gonna|need)\s+to\s+(die|kill\s+myself|end\s+(it|my\s+life))"
            r"|\bkill(ing)?\s+myself\b|\bhurt(ing)?\s+myself\b|\bcut(ting)?\s+myself\b"
            r"|\bsuicid|\bself[-\s]?harm\b|\bwant\s+to\s+disappear\b",
            re.I,
        ),
        _SUPPORT,
    ),
    (
        "weapons_howto",
        re.compile(
            r"\bhow\s+(to|do\s+i|can\s+i)\b.{0,40}\b(make|build|create|assemble|get)\b.{0,30}"
            r"\b(bomb|explosive|gun|firearm|grenade|poison|weapon)\b",
            re.I,
        ),
        _REDIRECT,
    ),
    (
        "harm_others",
        re.compile(
            r"\bhow\s+(to|do\s+i|can\s+i)\b.{0,40}\b(hurt|kill|harm|attack|poison|stab|shoot)\b.{0,20}"
            r"\b(someone|somebody|him|her|them|people|my\s+\w+|a\s+person)\b",
            re.I,
        ),
        _REDIRECT,
    ),
    (
        "substances",
        re.compile(
            r"\bhow\s+(to|do\s+i|can\s+i)\b.{0,40}\b(make|get|buy|score|use|take)\b.{0,20}"
            r"\b(drugs?|weed|marijuana|cocaine|meth|heroin|vape|cigarettes?|alcohol\s+to\s+get\s+drunk)\b",
            re.I,
        ),
        _REDIRECT,
    ),
    (
        "sexual_explicit",
        re.compile(
            r"\b(send|show|give)\s+(me\s+)?(nudes?|naked)\b|\bporn\b|\bsexth?ing\b|\bnude\s+(pic|photo|image)"
            r"|\bbe\s+my\s+(girlfriend|boyfriend)\b|\bsext\b|\bhorny\b|\bdirty\s+talk\b",
            re.I,
        ),
        "That's not something I can help with. I'm here for your schoolwork — ask me about your subject!",
    ),
    (
        "personal_contact",
        re.compile(
            r"\b(what('?s| is)\s+your|give\s+me\s+your|send\s+me\s+your)\b.{0,20}"
            r"\b(address|phone|number|whatsapp|insta(gram)?|snapchat|password)\b"
            r"|\bwhere\s+do\s+you\s+live\b|\bcan\s+(we|i)\s+meet\b|\bmeet\s+(me|up)\s+(in|at|irl)\b",
            re.I,
        ),
        "I can't share personal details or arrange to meet — I'm just your study assistant. "
        "Ask me about your lessons instead!",
    ),
    (
        "jailbreak",
        re.compile(
            r"\bignore\s+(all\s+|the\s+|your\s+|previous\s+|prior\s+)*(instructions?|prompts?|rules?)\b"
            r"|\byou\s+are\s+now\b|\bdeveloper\s+mode\b|\bpretend\s+you\s+(are|have\s+no)\b"
            r"|\bact\s+as\s+(if\s+you|an?\s+unrestricted)\b|\bdo\s+anything\s+now\b|\bDAN\b|\bjailbreak\b"
            r"|\bforget\s+(your|the|all)\s+(rules|instructions|guidelines)\b",
            re.I,
        ),
        "I can only help with your subject and chapter material. What would you like to learn?",
    ),
]


class GuardrailService:
    def __init__(
        self,
        llm: AbstractLLMProvider | None = None,
        model: str = "llama-3.1-8b-instant",
    ) -> None:
        self._llm = llm
        self._model = model

    # ── Layer 1: safety (deterministic, always runs) ─────────────────────────
    def check_safety(self, question: str) -> SafetyVerdict:
        q = (question or "").strip()
        for category, pattern, message in _SAFETY_RULES:
            if pattern.search(q):
                logger.info("guardrail_safety_block", category=category)
                return SafetyVerdict(blocked=True, category=category, message=message)
        return SafetyVerdict(blocked=False)

    # ── Layer 2: subject adherence (LLM; degrades to allow if no LLM/subject) ─
    async def check_subject_relevance(
        self, question: str, subject: str | None, chapter: str | None = None
    ) -> RelevanceVerdict:
        if not subject or not self._llm:
            return RelevanceVerdict(on_topic=True, confidence=1.0, reason="relevance check skipped")

        system = (
            "You are a strict topic gate for a K-12 subject tutor. Decide whether a "
            "student's question belongs to the given SUBJECT. A question is on_topic if it "
            "concerns the subject at all (even a different chapter of it). It is off-topic "
            "ONLY if it is unrelated to the subject — e.g. small talk, another subject, "
            "games, celebrities, or personal matters. Reply with JSON only."
        )
        user = (
            f"Subject: {subject}\nChapter (context only): {chapter or 'N/A'}\n"
            f'Student question: "{question}"\n\n'
            'Return JSON: {"on_topic": true|false, "confidence": 0..1, "reason": "short"}'
        )
        try:
            data = await llm_json(self._llm, self._model, system, user, max_tokens=200)
        except Exception as exc:  # LLM failure must not hard-block a legitimate learner
            logger.warning("guardrail_relevance_llm_failed", error=str(exc))
            return RelevanceVerdict(on_topic=True, confidence=0.0, reason="relevance check unavailable")

        return RelevanceVerdict(
            on_topic=bool(data.get("on_topic", True)),
            confidence=float(data.get("confidence", 0.5) or 0.5),
            reason=str(data.get("reason", "")),
        )
