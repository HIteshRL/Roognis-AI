"""
Learner-intelligence read models for the student dashboard.

Demo-mirror of the apps/api engines, derived fresh from the SQLite evidence log
on every call ("derive, don't store" — same principle as SkillGraphService):

  02 mastery-engine        -> mastery()         EMA fold over chronological evidence
  03 learning-gap-detector -> gaps()            negative signals, auto-resolve on recovery
  05 learning-velocity     -> analytics()       last-7d vs prior-7d activity trend
  06 skill-graph-engine    -> skills()          Bloom-level distribution, never persisted
  08 next-best-topic       -> recommendations() gap > review > new, with reasons
  11 learner-context       -> student_insights() the aggregate payload

Confidence is NEVER assumed: it comes from question_engine.concept_confidence
(agreement x coverage over the evidence log), identical to the questioning loop.
"""
import time

import question_engine
import store

_POS = {"correct", "recall_success"}
_NEG = {"incorrect", "misconception", "recall_fail"}
_EMA_KEEP = 0.7                     # same smoothing as the real MasteryEngine
_TARGET = {"correct": 100.0, "recall_success": 95.0, "partial": 60.0,
           "incorrect": 15.0, "misconception": 10.0, "recall_fail": 20.0}
_BLOOM_ORDER = ["remember", "understand", "apply", "analyze", "evaluate", "create"]
_DAY = 86400.0


def _label(score: float) -> str:
    if score < 40:
        return "struggling"
    if score < 60:
        return "developing"
    if score < 80:
        return "proficient"
    return "mastered"


def _by_concept(events: list[dict]) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for e in sorted(events, key=lambda x: x["created_at"] or 0):
        if e.get("concept"):
            out.setdefault(e["concept"], []).append(e)
    return out


def mastery(events: list[dict]) -> list[dict]:
    """EMA-smoothed mastery per concept (mirror of engine 02)."""
    out = []
    for concept, evs in _by_concept(events).items():
        score = 50.0
        for e in evs:
            target = _TARGET.get(e["signal"])
            if target is None:
                continue
            score = _EMA_KEEP * score + (1 - _EMA_KEEP) * target
        out.append({
            "concept": concept,
            "score": round(score, 1),
            "label": _label(score),
            "confidence": question_engine.concept_confidence(evs),
            "interactions": len(evs),
            "last_seen": evs[-1]["created_at"],
        })
    out.sort(key=lambda m: m["score"])
    return out


def gaps(events: list[dict]) -> list[dict]:
    """Active learning gaps from negative evidence (mirror of engine 03).
    A gap auto-resolves when the two most recent directional signals are positive."""
    out = []
    for concept, evs in _by_concept(events).items():
        directional = [e for e in evs if e["signal"] in _POS | _NEG | {"partial"}]
        neg = [e for e in directional if e["signal"] in _NEG]
        if not neg:
            continue
        tail = [e for e in directional if e["signal"] in _POS | _NEG][-2:]
        resolved = len(tail) == 2 and all(e["signal"] in _POS for e in tail)
        ratio = len(neg) / len(directional)
        severity = ("high" if len(neg) >= 2 and ratio >= 0.5
                    else "medium" if len(neg) >= 2 else "low")
        has_misconception = any(e["signal"] == "misconception" for e in neg)
        reason = ("misconception detected" if has_misconception
                  else f"{len(neg)} of {len(directional)} checks missed")
        out.append({
            "concept": concept, "severity": severity, "reason": reason,
            "occurrences": len(neg), "resolved": resolved,
            "last_seen": neg[-1]["created_at"],
        })
    order = {"high": 0, "medium": 1, "low": 2}
    out.sort(key=lambda g: (g["resolved"], order[g["severity"]], -g["occurrences"]))
    return out


def skills(questions: list[dict]) -> list[dict]:
    """Bloom-level skill profile from evaluated checks (mirror of engine 06)."""
    buckets: dict[str, dict] = {}
    for q in questions:
        if q["status"] != "evaluated" or not q.get("bloom_level"):
            continue
        b = buckets.setdefault(q["bloom_level"].lower(), {"attempted": 0, "correct": 0})
        b["attempted"] += 1
        b["correct"] += 1 if q["is_correct"] else 0
    return [
        {"level": lvl, "attempted": b["attempted"], "correct": b["correct"],
         "accuracy": round(b["correct"] / b["attempted"], 2)}
        for lvl in _BLOOM_ORDER if (b := buckets.get(lvl))
    ]


def recommendations(mastery_rows: list[dict], gap_rows: list[dict]) -> list[dict]:
    """Next-best-topic ranking (mirror of engine 08): close gaps, then shore up
    weak mastery, then start untouched chapters."""
    recs, seen = [], set()
    for g in gap_rows:
        if not g["resolved"]:
            recs.append({"concept": g["concept"], "type": "gap",
                         "reason": f"Close the gap — {g['reason']}"})
            seen.add(g["concept"])
    for m in mastery_rows:
        if m["concept"] not in seen and m["score"] < 60:
            recs.append({"concept": m["concept"], "type": "review",
                         "reason": f"Mastery at {m['score']:.0f} — a quick review would lift it"})
            seen.add(m["concept"])
    attempted = {m["concept"] for m in mastery_rows}
    for room in store.list_classrooms():
        for ch in store.list_chapters(room["id"]):
            if ch["title"] not in attempted and ch["title"] not in seen and ch["doc_count"] >= 0:
                recs.append({"concept": ch["title"], "type": "new",
                             "reason": f"Not attempted yet — next in {room['name']}"})
                seen.add(ch["title"])
    return recs[:5]


def timeline(student_id: str, questions: list[dict]) -> list[dict]:
    """Merged activity feed: conversations + evaluated checks, newest first."""
    items = [
        {"kind": "chat", "title": c["title"] or "Conversation",
         "meta": " · ".join(x for x in [c.get("classroom_name"), c.get("chapter_title")] if x),
         "at": c["updated_at"]}
        for c in store.list_conversations_for_student(student_id)
    ] + [
        {"kind": "check", "title": q["concept"],
         "meta": q["feedback"] or "", "correct": bool(q["is_correct"]),
         "score": q["score"], "at": q["answered_at"]}
        for q in questions if q["status"] == "evaluated"
    ]
    items.sort(key=lambda i: i["at"] or 0, reverse=True)
    return items[:20]


def analytics(events: list[dict], questions: list[dict]) -> dict:
    """Headline numbers + velocity trend (mirror of engine 05)."""
    now = time.time()
    answered = [q for q in questions if q["status"] == "evaluated"]
    correct = sum(1 for q in answered if q["is_correct"])
    stamps = ([e["created_at"] for e in events]
              + [q["answered_at"] for q in answered if q["answered_at"]])
    active_days = len({time.strftime("%Y-%m-%d", time.localtime(t)) for t in stamps if t})
    last7 = sum(1 for t in stamps if t and now - t <= 7 * _DAY)
    prev7 = sum(1 for t in stamps if t and 7 * _DAY < now - t <= 14 * _DAY)
    velocity = ("accelerating" if last7 > prev7
                else "steady" if last7 == prev7 else "slowing")
    return {
        "checks_answered": len(answered),
        "accuracy": round(correct / len(answered), 2) if answered else None,
        "evidence_events": len(events),
        "concepts_touched": len({e["concept"] for e in events if e.get("concept")}),
        "active_days": active_days,
        "velocity": velocity if stamps else "no activity yet",
    }


def student_insights(student_id: str) -> dict:
    """The aggregate learner context for the dashboard (mirror of engine 11)."""
    events = store.list_evidence(student_id, limit=1000)
    questions = store.list_questions(student_id, limit=500)
    mastery_rows = mastery(events)
    gap_rows = gaps(events)
    return {
        "mastery": mastery_rows,
        "gaps": gap_rows,
        "skills": skills(questions),
        "recommendations": recommendations(mastery_rows, gap_rows),
        "timeline": timeline(student_id, questions),
        "analytics": analytics(events, questions),
    }
