import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.system import PromptTemplateModel

logger = structlog.get_logger(__name__)

# Fallback prompts used only when the database has no record for that template name.
# These should be seeded into the prompt_templates table on first run.
_FALLBACKS: dict[str, str] = {
    "default_system": (
        "You are Roognis, an intelligent AI learning assistant. "
        "You help learners understand concepts clearly, build knowledge systematically, "
        "and stay motivated on their learning journey. "
        "Be concise, accurate, and encouraging."
    ),
}


class PromptLoader:
    """
    Loads prompt templates from the database.
    Falls back to in-memory defaults only when a DB record is absent.
    Never hardcodes prompt logic inside business services.
    """

    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._cache: dict[str, str] = {}

    async def get(self, name: str) -> str:
        if name in self._cache:
            return self._cache[name]

        result = await self._db.execute(
            select(PromptTemplateModel).where(
                PromptTemplateModel.name == name,
                PromptTemplateModel.is_active == True,  # noqa: E712
            )
        )
        template = result.scalar_one_or_none()

        if template:
            self._cache[name] = template.template
            return template.template

        fallback = _FALLBACKS.get(name, "")
        if not fallback:
            logger.warning("prompt_template_missing", name=name)
        return fallback

    def invalidate(self, name: str) -> None:
        self._cache.pop(name, None)
