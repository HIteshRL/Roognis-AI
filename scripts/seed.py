"""
Seed script.

Always: inserts default prompt templates.
Opt-in (SEED_DEMO=1): inserts a full demo dataset so every dashboard renders
populated on first login — one student, teacher, and parent, a school +
classroom (join code DEMO24) with published syllabus, a Grade-8 Math concept
graph, mastery records, active gaps, recent sessions, and a guardian link.

Run:  python scripts/seed.py
Demo: SEED_DEMO=1 python scripts/seed.py

Idempotent: the demo block is skipped if the demo student already exists, so it
is safe to run on every container boot (docker-compose runs this before uvicorn).
"""
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "apps" / "api"))

from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.config import get_settings
from src.domain.entities.guardian import GuardianLink
from src.domain.entities.learning import (
    BehavioralSignals,
    ConceptEdge,
    LearningSession,
    StudentProfile,
)
from src.domain.entities.school import (
    Classroom,
    Enrollment,
    Role,
    School,
    SchoolMember,
    SyllabusItem,
)
from src.domain.entities.user import User
from src.infrastructure.database.models.system import PromptTemplateModel
from src.infrastructure.database.repositories.guardian_repository import GuardianRepository
from src.infrastructure.database.repositories.learning_repository import (
    ConceptEdgeRepository,
    ConceptNodeRepository,
    LearningGapRepository,
    LearningSessionRepository,
    MasteryRepository,
    StudentProfileRepository,
)
from src.infrastructure.database.repositories.school_repository import (
    ClassroomRepository,
    EnrollmentRepository,
    SchoolMemberRepository,
    SchoolRepository,
    SyllabusRepository,
)
from src.infrastructure.database.repositories.user_repository import UserRepository

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

DEMO_PASSWORD = "Demo1234!"
DEMO_JOIN_CODE = "DEMO24"
DEMO_STUDENT_EMAIL = "kid1@demo.roognis.ai"

# Five demo students for the classroom (username, email tag, target avg mastery
# 0-100 or None for a brand-new kid with no records yet). Spread across the
# mastery buckets so the teacher dashboard shows a realistic distribution.
DEMO_KIDS = [
    ("aarav", "kid1", 88),   # mastered
    ("diya", "kid2", 72),    # proficient
    ("kabir", "kid3", 48),   # developing
    ("meera", "kid4", 24),   # struggling
    ("rohan", "kid5", None),  # just joined — no mastery yet
]

PROMPT_TEMPLATES = [
    {
        "name": "default_system",
        "description": "Main system prompt for the Roognis AI assistant",
        "template": (
            "You are Roognis, an intelligent AI learning assistant. "
            "You help learners understand concepts clearly, build knowledge systematically, "
            "and stay motivated on their learning journey. "
            "Be concise, accurate, and encouraging. "
            "When explaining technical concepts, use clear examples. "
            "Adapt your language to the learner's apparent level."
        ),
        "variables": [],
        "is_active": True,
    },
]

# (concept name, mastery score 0-100)
DEMO_CONCEPTS = [
    ("Fractions", 82),
    ("Equivalent Fractions", 74),
    ("Adding Fractions", 68),
    ("Decimals", 55),
    ("Fraction-Decimal Conversion", 40),
    ("Ratios", 48),
    ("Proportions", 30),
    ("Percentages", 25),
]
DEMO_PREREQS = [
    ("Fractions", "Equivalent Fractions"),
    ("Equivalent Fractions", "Adding Fractions"),
    ("Fractions", "Fraction-Decimal Conversion"),
    ("Decimals", "Fraction-Decimal Conversion"),
    ("Ratios", "Proportions"),
    ("Proportions", "Percentages"),
]
DEMO_SESSIONS = [
    ("How do I add 1/2 and 1/4?", "Adding Fractions"),
    ("What is 0.75 as a fraction?", "Fraction-Decimal Conversion"),
    ("Explain equivalent fractions", "Equivalent Fractions"),
    ("How do ratios work?", "Ratios"),
    ("Convert 3/5 to a percentage", "Percentages"),
]


async def seed_prompt_templates(db) -> None:
    for data in PROMPT_TEMPLATES:
        result = await db.execute(
            select(PromptTemplateModel).where(PromptTemplateModel.name == data["name"])
        )
        if result.scalar_one_or_none():
            print(f"Skipped prompt template (exists): {data['name']}")
        else:
            db.add(PromptTemplateModel(**data))
            print(f"Seeded prompt template: {data['name']}")
    await db.commit()


async def seed_demo(db) -> None:
    users = UserRepository(db)
    if await users.get_by_email(DEMO_STUDENT_EMAIL):
        print("Demo data already present — skipping demo seed.")
        return

    ph = _pwd.hash(DEMO_PASSWORD)
    teacher = await users.create(
        User(email="teacher@demo.roognis.ai", username="demo_teacher",
             password_hash=ph, role=Role.TEACHER, is_verified=True)
    )
    parent = await users.create(
        User(email="parent@demo.roognis.ai", username="demo_parent",
             password_hash=ph, role=Role.PARENT, is_verified=True)
    )

    # School + classroom + published syllabus (owned by the teacher).
    school = await SchoolRepository(db).create(
        School(name="Demo Public School", slug="demo-public-school", created_by=teacher.id)
    )
    await SchoolMemberRepository(db).create(
        SchoolMember(school_id=school.id, user_id=teacher.id, role=Role.SCHOOL_ADMIN)
    )
    classroom = await ClassroomRepository(db).create(
        Classroom(school_id=school.id, name="Grade 8 Mathematics", subject="Mathematics",
                  grade="8", teacher_id=teacher.id, join_code=DEMO_JOIN_CODE)
    )
    syllabus = SyllabusRepository(db)
    for i, chapter in enumerate(["Fractions", "Decimals", "Ratios & Proportions"]):
        await syllabus.create(
            SyllabusItem(classroom_id=classroom.id, subject="Mathematics",
                         chapter=chapter, order_index=i, is_published=True)
        )

    # Shared concept graph (created once, referenced by every kid's mastery).
    nodes_repo, edges_repo = ConceptNodeRepository(db), ConceptEdgeRepository(db)
    nodes = {}
    for name, _ in DEMO_CONCEPTS:
        nodes[name] = await nodes_repo.get_or_create(name, "Mathematics", "8", "Fractions & Decimals")
    for src, tgt in DEMO_PREREQS:
        await edges_repo.create(ConceptEdge(source_id=nodes[src].id, target_id=nodes[tgt].id))

    profiles = StudentProfileRepository(db)
    enrollments = EnrollmentRepository(db)
    mastery_repo = MasteryRepository(db)
    gap_repo = LearningGapRepository(db)
    sessions_repo = LearningSessionRepository(db)
    streaks = [6, 4, 3, 2, 1]
    session_counts = [4, 3, 3, 2, 1]
    first_student = None

    for idx, (username, tag, target) in enumerate(DEMO_KIDS):
        student = await users.create(
            User(email=f"{tag}@demo.roognis.ai", username=username,
                 password_hash=ph, role=Role.STUDENT, is_verified=True)
        )
        first_student = first_student or student

        await profiles.create(
            StudentProfile(
                user_id=student.id, grade="8", subjects=["Mathematics"],
                current_chapter="Fractions & Decimals",
                behavioral_signals=BehavioralSignals(
                    engagement_streak=streaks[idx % len(streaks)],
                    dominant_subject="Mathematics",
                ),
            )
        )
        await enrollments.create(Enrollment(classroom_id=classroom.id, student_id=student.id))

        if target is not None:
            for ci, (name, _base) in enumerate(DEMO_CONCEPTS):
                rec = await mastery_repo.get_or_create(student.id, nodes[name].id, name)
                rec.score = max(0.0, min(100.0, float(target + (ci - 4) * 3)))
                rec.interaction_count = 3
                await mastery_repo.update(rec)
            if target < 60:
                g = await gap_repo.get_or_create(
                    student.id, nodes["Proportions"].id, "Proportions",
                    "Confuses ratio direction when setting up proportions",
                )
                g.severity, g.confidence, g.occurrence_count = "high", "high", 3
                await gap_repo.update(g)
            if target < 35:
                await gap_repo.get_or_create(
                    student.id, nodes["Percentages"].id, "Percentages",
                    "Struggles converting percentages to fractions",
                )

        for question, concept in DEMO_SESSIONS[: session_counts[idx % len(session_counts)]]:
            await sessions_repo.create(
                LearningSession(
                    user_id=student.id, question=question,
                    ai_response="(demo) Here's a clear explanation with a worked example…",
                    subject="Mathematics", chapter="Fractions & Decimals", grade="8",
                    primary_concept=concept, concepts_discussed=[concept],
                    bloom_level="Apply", difficulty_level="medium", intent="concept_explanation",
                )
            )

    # Parent follows the first child, so the parent portal demo has data.
    await GuardianRepository(db).create(
        GuardianLink(parent_id=parent.id, student_id=first_student.id)
    )

    await db.commit()
    logins = ", ".join(f"{tag}@demo.roognis.ai" for _, tag, _ in DEMO_KIDS)
    print(
        f"Demo seeded (password '{DEMO_PASSWORD}'): teacher@demo.roognis.ai, "
        f"parent@demo.roognis.ai, and {len(DEMO_KIDS)} students [{logins}] — "
        f"all enrolled in Grade 8 Mathematics (join code {DEMO_JOIN_CODE})."
    )


async def seed() -> None:
    settings = get_settings()
    engine = create_async_engine(settings.database_url_str)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as db:
        await seed_prompt_templates(db)
        if os.getenv("SEED_DEMO", "").lower() in ("1", "true", "yes"):
            await seed_demo(db)

    await engine.dispose()
    print("Seeding complete.")


if __name__ == "__main__":
    asyncio.run(seed())
