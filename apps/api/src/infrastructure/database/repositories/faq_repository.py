from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.faq import FaqEntry
from src.domain.repositories.faq_repository import AbstractFaqRepository
from src.infrastructure.database.models.faq import FaqEntryModel


def _to_entry(m: FaqEntryModel) -> FaqEntry:
    e = FaqEntry.__new__(FaqEntry)
    e.id = UUID(m.id)
    e.cache_key = m.cache_key
    e.normalized_query = m.normalized_query
    e.question = m.question
    e.answer = m.answer
    e.subject = m.subject
    e.grade = m.grade
    e.hit_count = m.hit_count
    e.source = m.source
    e.created_at = m.created_at
    e.updated_at = m.updated_at
    e.last_hit_at = m.last_hit_at
    return e


class FaqRepository(AbstractFaqRepository):
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_by_cache_key(self, cache_key: str) -> FaqEntry | None:
        result = await self._db.execute(
            select(FaqEntryModel).where(FaqEntryModel.cache_key == cache_key)
        )
        m = result.scalar_one_or_none()
        return _to_entry(m) if m else None

    async def upsert_hit(self, entry: FaqEntry) -> FaqEntry:
        result = await self._db.execute(
            select(FaqEntryModel).where(FaqEntryModel.cache_key == entry.cache_key)
        )
        m = result.scalar_one_or_none()
        if m:
            m.hit_count = m.hit_count + 1
            m.last_hit_at = func.now()
            m.answer = entry.answer
        else:
            m = FaqEntryModel(
                id=str(entry.id),
                cache_key=entry.cache_key,
                normalized_query=entry.normalized_query,
                question=entry.question,
                answer=entry.answer,
                subject=entry.subject,
                grade=entry.grade,
                hit_count=entry.hit_count,
                source=entry.source,
            )
            self._db.add(m)
        await self._db.flush()
        await self._db.refresh(m)
        return _to_entry(m)

    async def list_top(self, subject: str | None, limit: int) -> list[FaqEntry]:
        stmt = (
            select(FaqEntryModel)
            .order_by(FaqEntryModel.hit_count.desc(), FaqEntryModel.last_hit_at.desc())
            .limit(limit)
        )
        if subject:
            stmt = stmt.where(FaqEntryModel.subject == subject)
        result = await self._db.execute(stmt)
        return [_to_entry(m) for m in result.scalars().all()]

    async def search(self, term: str, limit: int) -> list[FaqEntry]:
        like = f"%{term.lower()}%"
        result = await self._db.execute(
            select(FaqEntryModel)
            .where(
                or_(
                    func.lower(FaqEntryModel.question).like(like),
                    FaqEntryModel.normalized_query.like(like),
                )
            )
            .order_by(FaqEntryModel.hit_count.desc())
            .limit(limit)
        )
        return [_to_entry(m) for m in result.scalars().all()]

    async def count(self) -> int:
        result = await self._db.execute(select(func.count(FaqEntryModel.id)))
        return result.scalar_one()
