"""
Skill Graph Engine — Roognis AI (Phase 0.5)

Derives a student's skill profile from mastery records + session history.
Maps Bloom taxonomy levels to competency domains so the UI can show
"what skills this student is strong at" rather than just a list of concepts.

No database access. No external packages. Pure computation.
"""
from domain import BLOOM_LEVELS, LearningSession, MasteryRecord

BLOOM_TO_SKILLS: dict[str, list[str]] = {
    "Remember":   ["Knowledge Recall", "Memorization"],
    "Understand": ["Conceptual Understanding", "Reading Comprehension"],
    "Apply":      ["Problem Solving", "Procedural Execution"],
    "Analyze":    ["Critical Analysis", "Pattern Recognition"],
    "Evaluate":   ["Critical Thinking", "Judgment & Evaluation"],
    "Create":     ["Synthesis", "Creative Thinking"],
}

_BLOOM_WEIGHT = {level: (i + 1) for i, level in enumerate(BLOOM_LEVELS)}


class SkillGraphService:
    def derive_skills_for_bloom(self, bloom_level: str) -> list[str]:
        return BLOOM_TO_SKILLS.get(bloom_level, [])

    def build_student_skill_profile(
        self,
        mastery_records: list[MasteryRecord],
        sessions: list[LearningSession],
    ) -> dict[str, float]:
        skill_scores: dict[str, list[float]] = {}
        concept_bloom: dict[str, str] = {}
        for s in sessions:
            if s.primary_concept and s.bloom_level:
                concept_bloom[s.primary_concept] = s.bloom_level
            for c in s.concepts_discussed:
                if c and s.bloom_level and c not in concept_bloom:
                    concept_bloom[c] = s.bloom_level

        for record in mastery_records:
            bloom = concept_bloom.get(record.concept_name, "Understand")
            for skill in self.derive_skills_for_bloom(bloom):
                skill_scores.setdefault(skill, []).append(record.score)

        if not concept_bloom:
            for record in mastery_records:
                if record.score >= 85: bloom = "Evaluate"
                elif record.score >= 70: bloom = "Apply"
                elif record.score >= 50: bloom = "Understand"
                else: bloom = "Remember"
                for skill in self.derive_skills_for_bloom(bloom):
                    skill_scores.setdefault(skill, []).append(record.score)

        return {
            skill: round(sum(scores) / len(scores), 1)
            for skill, scores in skill_scores.items() if scores
        }

    def top_skills(self, profile: dict[str, float], n: int = 5) -> list[dict]:
        return [{"skill": k, "proficiency": v}
                for k, v in sorted(profile.items(), key=lambda x: x[1], reverse=True)[:n]]

    def categorize_bloom_distribution(self, sessions: list[LearningSession]) -> dict[str, int]:
        dist: dict[str, int] = {level: 0 for level in BLOOM_LEVELS}
        for s in sessions:
            if s.bloom_level in dist:
                dist[s.bloom_level] += 1
        return dist
