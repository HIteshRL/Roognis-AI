"""Phase A — Psychometric Assessment Service (roadmap v0.3).

Delivers the survey incrementally, scores answers with a deterministic rubric
(no LLM), and produces a merged `PsychometricProfile` where surveyed
dimensions take precedence over values inferred from existing behavioral
signals. Fully derive-on-read: `get_profile` recomputes from stored responses
+ current behavioral signals every call, so it never goes stale.
"""
from datetime import UTC, datetime
from uuid import UUID

import structlog

from src.application.services.psychometric_questions import (
    QUESTIONS,
    QUESTIONS_BY_KEY,
    TOTAL_QUESTIONS,
    is_valid_answer,
    likert_norm,
    public_question,
)
from src.domain.entities.psychometric import (
    SOURCE_INFERRED,
    SOURCE_SURVEY,
    PsychometricProfile,
    PsychometricResponse,
)
from src.domain.exceptions import ValidationError
from src.domain.repositories.learning_repository import AbstractStudentProfileRepository
from src.domain.repositories.psychometric_repository import AbstractPsychometricRepository

logger = structlog.get_logger(__name__)

_MOTIVATION_TIE = 0.15   # |intrinsic - extrinsic| below this reads as "mixed"
_MIN_BEHAVIOR_SESSIONS = 3   # need this much history before inferring anything


class PsychometricAssessmentService:
    def __init__(
        self,
        psychometric_repo: AbstractPsychometricRepository,
        profile_repo: AbstractStudentProfileRepository,
    ) -> None:
        self._repo = psychometric_repo
        self._profiles = profile_repo

    # ── Survey delivery ───────────────────────────────────────────────────
    async def get_pending_questions(self, user_id: UUID, limit: int = 5) -> list[dict]:
        answered = await self._repo.answered_keys(user_id)
        pending = [public_question(q) for q in QUESTIONS if q["key"] not in answered]
        return pending[:limit]

    async def record_response(
        self, user_id: UUID, question_key: str, value: str, raw: str | None = None
    ) -> PsychometricProfile:
        q = QUESTIONS_BY_KEY.get(question_key)
        if q is None:
            raise ValidationError(f"Unknown question: {question_key}")
        if not is_valid_answer(q, value):
            raise ValidationError(f"Invalid answer '{value}' for question {question_key}")

        await self._repo.upsert_response(
            PsychometricResponse(
                user_id=user_id,
                question_key=question_key,
                dimension=q["dimension"],
                response_value=value,
                question_text=q["text"],
                response_raw=raw,
            )
        )
        profile = await self._build_profile(user_id)
        await self._repo.save_profile(user_id, profile)
        return profile

    async def get_profile(self, user_id: UUID) -> PsychometricProfile:
        return await self._build_profile(user_id)

    # ── Core scoring ──────────────────────────────────────────────────────
    async def _build_profile(self, user_id: UUID) -> PsychometricProfile:
        responses = await self._repo.list_responses(user_id)
        by_key = {r.question_key: r.response_value for r in responses}

        surveyed, sources = self._score_surveyed(by_key)

        behavioral = None
        try:
            profile = await self._profiles.get_by_user_id(user_id)
            if profile is not None:
                behavioral = (profile.behavioral_signals, profile.confidence_score)
        except Exception:
            behavioral = None

        inferred = self._infer_from_behavior(behavioral) if behavioral else {}

        merged = dict(surveyed)
        for dim, val in inferred.items():
            if dim not in merged:
                merged[dim] = val
                sources[dim] = SOURCE_INFERRED

        result = PsychometricProfile(
            sources=sources,
            completeness=round(len(by_key) / TOTAL_QUESTIONS, 3),
            assessed_at=datetime.now(UTC).isoformat() if by_key else None,
        )
        mot = merged.get("motivation")
        if mot:
            result.motivation_type = mot["type"]
            result.motivation_strength = mot["strength"]
        if "discipline" in merged:
            result.discipline = merged["discipline"]
        if "interest" in merged:
            result.interests = merged["interest"]
        if "learning_style" in merged:
            result.learning_style_preference = merged["learning_style"]
        if "confidence" in merged:
            result.confidence_self_report = merged["confidence"]
        return result

    @staticmethod
    def _score_surveyed(by_key: dict[str, str]) -> tuple[dict, dict[str, str]]:
        surveyed: dict = {}
        sources: dict[str, str] = {}

        # ── Motivation ────────────────────────────────────────────────────
        intrinsic_ev: list[float] = []
        extrinsic_ev: list[float] = []
        driver = by_key.get("mot_driver")
        if driver == "intrinsic":
            intrinsic_ev.append(1.0)
            extrinsic_ev.append(0.0)
        elif driver == "extrinsic":
            intrinsic_ev.append(0.0)
            extrinsic_ev.append(1.0)
        elif driver == "mixed":
            intrinsic_ev.append(0.5)
            extrinsic_ev.append(0.5)
        for key in ("mot_explore", "mot_enjoy"):
            if key in by_key:
                intrinsic_ev.append(likert_norm(by_key[key]))
        if "mot_grades" in by_key:
            extrinsic_ev.append(likert_norm(by_key["mot_grades"]))

        if intrinsic_ev or extrinsic_ev:
            i = sum(intrinsic_ev) / len(intrinsic_ev) if intrinsic_ev else 0.0
            e = sum(extrinsic_ev) / len(extrinsic_ev) if extrinsic_ev else 0.0
            if abs(i - e) <= _MOTIVATION_TIE:
                mtype = "mixed"
            elif i > e:
                mtype = "intrinsic"
            else:
                mtype = "extrinsic"
            surveyed["motivation"] = {"type": mtype, "strength": round(max(i, e), 2)}
            sources["motivation"] = SOURCE_SURVEY

        # ── Discipline ────────────────────────────────────────────────────
        dis: list[float] = []
        for key in ("dis_schedule", "dis_finish", "dis_breakdown"):
            if key in by_key:
                dis.append(likert_norm(by_key[key]))
        if "dis_distract" in by_key:
            dis.append(likert_norm(by_key["dis_distract"], reverse=True))
        if dis:
            surveyed["discipline"] = round(sum(dis) / len(dis), 2)
            sources["discipline"] = SOURCE_SURVEY

        # ── Confidence ────────────────────────────────────────────────────
        conf: list[float] = []
        for key in ("conf_master", "conf_recover"):
            if key in by_key:
                conf.append(likert_norm(by_key[key]))
        if "conf_doubt" in by_key:
            conf.append(likert_norm(by_key["conf_doubt"], reverse=True))
        if conf:
            surveyed["confidence"] = round(sum(conf) / len(conf), 2)
            sources["confidence"] = SOURCE_SURVEY

        # ── Interest (ranked) ─────────────────────────────────────────────
        interests: list[str] = []
        for key in ("int_primary", "int_secondary"):
            v = by_key.get(key)
            if v and v not in interests:
                interests.append(v)
        if interests:
            surveyed["interest"] = interests
            sources["interest"] = SOURCE_SURVEY

        # ── Learning style ────────────────────────────────────────────────
        style = by_key.get("ls_primary") or by_key.get("ls_stuck")
        if style:
            surveyed["learning_style"] = style
            sources["learning_style"] = SOURCE_SURVEY

        return surveyed, sources

    @staticmethod
    def _infer_from_behavior(behavioral) -> dict:
        bs, confidence_score = behavioral
        if bs.total_sessions < _MIN_BEHAVIOR_SESSIONS:
            return {}

        inferred: dict = {}

        streak_norm = min(bs.engagement_streak / 14.0, 1.0)
        freq_norm = min(bs.sessions_per_day / 2.0, 1.0)
        inferred["discipline"] = round(0.6 * streak_norm + 0.4 * freq_norm, 2)

        if bs.question_complexity_trend == "rising":
            inferred["motivation"] = {"type": "intrinsic", "strength": 0.6}
        else:
            inferred["motivation"] = {"type": "mixed", "strength": round(0.3 + 0.5 * freq_norm, 2)}

        if confidence_score:
            inferred["confidence"] = round(min(max(confidence_score, 0.0), 1.0), 2)

        topics: list[str] = []
        if bs.dominant_subject:
            topics.append(bs.dominant_subject)
        for t in bs.recent_topics:
            if t not in topics:
                topics.append(t)
        if topics:
            inferred["interest"] = topics[:3]

        style_map = {"procedural": "hands_on", "conceptual": "reading"}
        if bs.response_pattern in style_map:
            inferred["learning_style"] = style_map[bs.response_pattern]

        return inferred
