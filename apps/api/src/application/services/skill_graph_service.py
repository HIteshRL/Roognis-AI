"""
Phase 0.5: Skill Graph Service.

Derives a student's skill profile from their mastery records and session
history. Maps Bloom taxonomy levels and concept domains to competency
categories so the frontend can display "what skills this student is strong at"
rather than just a list of concepts.

No new database tables — this is entirely derived from existing mastery + session data.
"""

from src.domain.entities.learning import BLOOM_LEVELS, LearningSession, MasteryRecord

# Maps each Bloom level to the primary skill domains it exercises
BLOOM_TO_SKILLS: dict[str, list[str]] = {
    "Remember":  ["Knowledge Recall", "Memorization"],
    "Understand": ["Conceptual Understanding", "Reading Comprehension"],
    "Apply":     ["Problem Solving", "Procedural Execution"],
    "Analyze":   ["Critical Analysis", "Pattern Recognition"],
    "Evaluate":  ["Critical Thinking", "Judgment & Evaluation"],
    "Create":    ["Synthesis", "Creative Thinking"],
}

# Bloom rank weights — higher-order skills count more toward overall proficiency
_BLOOM_WEIGHT = {level: (i + 1) for i, level in enumerate(BLOOM_LEVELS)}


class SkillGraphService:
    def derive_skills_for_bloom(self, bloom_level: str) -> list[str]:
        return BLOOM_TO_SKILLS.get(bloom_level, [])

    def build_student_skill_profile(
        self,
        mastery_records: list[MasteryRecord],
        sessions: list[LearningSession],
    ) -> dict[str, float]:
        """
        Returns skill_domain → proficiency (0-100) derived from mastery + session data.
        Each skill domain's proficiency is the weighted average mastery score of all
        concepts exercised at that Bloom level.
        """
        skill_scores: dict[str, list[float]] = {}

        # Weight mastery records by the Bloom level they map through sessions
        # Build concept → bloom_level map from recent sessions
        concept_bloom: dict[str, str] = {}
        for s in sessions:
            if s.primary_concept and s.bloom_level:
                concept_bloom[s.primary_concept] = s.bloom_level
            for c in s.concepts_discussed:
                if c and s.bloom_level and c not in concept_bloom:
                    concept_bloom[c] = s.bloom_level

        for record in mastery_records:
            bloom = concept_bloom.get(record.concept_name, "Understand")
            skills = self.derive_skills_for_bloom(bloom)
            for skill in skills:
                if skill not in skill_scores:
                    skill_scores[skill] = []
                skill_scores[skill].append(record.score)

        # If no session data, derive skills from mastery score distribution
        if not concept_bloom:
            for record in mastery_records:
                # Estimate Bloom level from mastery score (higher score → higher-order capable)
                if record.score >= 85:
                    bloom = "Evaluate"
                elif record.score >= 70:
                    bloom = "Apply"
                elif record.score >= 50:
                    bloom = "Understand"
                else:
                    bloom = "Remember"
                for skill in self.derive_skills_for_bloom(bloom):
                    skill_scores.setdefault(skill, []).append(record.score)

        return {
            skill: round(sum(scores) / len(scores), 1)
            for skill, scores in skill_scores.items()
            if scores
        }

    def top_skills(
        self,
        profile: dict[str, float],
        n: int = 5,
    ) -> list[dict]:
        """Returns top-n skills sorted by proficiency descending."""
        sorted_skills = sorted(profile.items(), key=lambda x: x[1], reverse=True)
        return [{"skill": k, "proficiency": v} for k, v in sorted_skills[:n]]

    def categorize_bloom_distribution(
        self, sessions: list[LearningSession]
    ) -> dict[str, int]:
        """Counts sessions by Bloom level for distribution charts."""
        dist: dict[str, int] = {level: 0 for level in BLOOM_LEVELS}
        for s in sessions:
            if s.bloom_level in dist:
                dist[s.bloom_level] += 1
        return dist
