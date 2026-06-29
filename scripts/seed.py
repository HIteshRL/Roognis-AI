"""
Seed script — inserts default prompt templates into the database.
Run: python scripts/seed.py
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "apps" / "api"))

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.config import get_settings
from src.infrastructure.database.models.system import PromptTemplateModel

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


async def seed() -> None:
    settings = get_settings()
    engine = create_async_engine(settings.database_url_str)
    Session = async_sessionmaker(engine, expire_on_commit=False)

    async with Session() as db:
        for template_data in PROMPT_TEMPLATES:
            from sqlalchemy import select
            result = await db.execute(
                select(PromptTemplateModel).where(
                    PromptTemplateModel.name == template_data["name"]
                )
            )
            existing = result.scalar_one_or_none()
            if not existing:
                db.add(PromptTemplateModel(**template_data))
                print(f"Seeded prompt template: {template_data['name']}")
            else:
                print(f"Skipped (already exists): {template_data['name']}")

        await db.commit()

    await engine.dispose()
    print("Seeding complete.")


if __name__ == "__main__":
    asyncio.run(seed())
