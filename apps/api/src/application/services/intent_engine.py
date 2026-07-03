"""
Phase 0.5: Intent Engine.

Classifies each student message into a pedagogical intent category using
rule-based pattern matching. Synchronous and zero-latency — runs before the
LLM call so the intent can shape the system prompt and be stored on the session.

Intent categories:
  correction_request   — student disputes or corrects the AI
  test_prep            — preparing for exams, quizzes, or practice
  clarification        — asking to re-explain or simplify something said
  recall               — short factual retrieval (definitions, names, dates)
  problem_solving      — computational or step-by-step task
  concept_explanation  — understanding the "why" or "how" of a concept
  unknown              — fallback when no pattern matches strongly
"""

_CORRECTION = [
    "wrong", "incorrect", "mistake", "error", "not right", "that's wrong",
    "you're wrong", "i think you", "disagree", "you said", "but you said",
]
_TEST_PREP = [
    "exam", "test", "quiz", "practice", "revision", "mock", "past paper",
    "prepare for", "important questions", "cbse", "board exam", "ncert questions",
]
_CLARIFICATION = [
    "don't understand", "dont understand", "not clear", "confused",
    "clarify", "explain again", "re-explain", "what do you mean",
    "i didn't get", "i didnt get", "elaborate", "in simpler terms",
    "can you explain", "still confused",
]
_RECALL = [
    "what is", "define ", "definition of", "who is", "who was",
    "when did", "when was", "where is", "where was", "list the",
    "name the", "state the", "give example of",
]
_PROBLEM_SOLVING = [
    "solve", "calculate", "find the value", "compute", "evaluate",
    "how many", "how much", "how do i", "how to solve", "steps to",
    "work out", "what is the answer", "find x", "find y",
]
_CONCEPT_EXPLANATION = [
    "why does", "why is", "why do", "why are", "how does",
    "how do ", "explain ", "what happens when", "difference between",
    "compare", "relation between", "effect of", "what causes",
]


class IntentEngine:
    def classify(self, question: str) -> str:
        q = question.lower().strip()

        if any(p in q for p in _CORRECTION):
            return "correction_request"

        if any(p in q for p in _TEST_PREP):
            return "test_prep"

        if any(p in q for p in _CLARIFICATION):
            return "clarification"

        if any(p in q for p in _PROBLEM_SOLVING):
            return "problem_solving"

        if any(p in q for p in _RECALL) and len(q.split()) <= 10:
            return "recall"

        if any(p in q for p in _CONCEPT_EXPLANATION):
            return "concept_explanation"

        # Default: any remaining "what is" that was too long for recall
        if "what is" in q or "what are" in q:
            return "concept_explanation"

        return "unknown"
