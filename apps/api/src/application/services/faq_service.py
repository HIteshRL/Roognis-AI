from src.domain.entities.faq import FaqEntry
from src.domain.repositories.faq_repository import AbstractFaqRepository


class FaqService:
    """Read side of the FAQ Knowledge Base — powers the public /faq endpoints."""

    def __init__(self, faq_repo: AbstractFaqRepository) -> None:
        self._faq = faq_repo

    async def list_top(self, subject: str | None, limit: int = 20) -> list[FaqEntry]:
        return await self._faq.list_top(subject, min(limit, 100))

    async def search(self, term: str, limit: int = 20) -> list[FaqEntry]:
        term = term.strip()
        if not term:
            return []
        return await self._faq.search(term, min(limit, 100))
