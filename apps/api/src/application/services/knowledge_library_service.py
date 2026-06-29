from uuid import UUID

import structlog

from src.application.dtos.knowledge import CreateKnowledgeBaseRequest, KnowledgeBaseResponse
from src.domain.entities.knowledge import KnowledgeBase
from src.domain.exceptions import EntityNotFound
from src.domain.repositories.knowledge_repository import (
    AbstractDocumentRepository,
    AbstractKnowledgeBaseRepository,
)

logger = structlog.get_logger(__name__)


class KnowledgeLibraryService:
    def __init__(
        self,
        kb_repo: AbstractKnowledgeBaseRepository,
        doc_repo: AbstractDocumentRepository,
    ) -> None:
        self._kbs = kb_repo
        self._docs = doc_repo

    async def create(self, dto: CreateKnowledgeBaseRequest, user_id: UUID) -> KnowledgeBaseResponse:
        kb = KnowledgeBase(
            name=dto.name,
            description=dto.description,
            institution=dto.institution,
            subject=dto.subject,
            language=dto.language,
            created_by=user_id,
        )
        kb = await self._kbs.create(kb)
        logger.info("knowledge_base_created", kb_id=str(kb.id), name=kb.name)
        return await self._to_response(kb)

    async def get(self, kb_id: UUID) -> KnowledgeBaseResponse:
        kb = await self._kbs.get_by_id(kb_id)
        if not kb:
            raise EntityNotFound("Knowledge base not found")
        return await self._to_response(kb)

    async def list(self, page: int, limit: int) -> tuple[list[KnowledgeBaseResponse], int]:
        kbs, total = await self._kbs.list_all(page, limit)
        responses = [await self._to_response(kb) for kb in kbs]
        return responses, total

    async def delete(self, kb_id: UUID) -> None:
        kb = await self._kbs.get_by_id(kb_id)
        if not kb:
            raise EntityNotFound("Knowledge base not found")
        await self._kbs.delete(kb_id)

    async def _to_response(self, kb: KnowledgeBase) -> KnowledgeBaseResponse:
        _, doc_count = await self._docs.list_by_knowledge_base(kb.id, page=1, limit=1)
        return KnowledgeBaseResponse(
            id=str(kb.id),
            name=kb.name,
            description=kb.description,
            institution=kb.institution,
            subject=kb.subject,
            language=kb.language,
            is_active=kb.is_active,
            created_by=str(kb.created_by),
            document_count=doc_count,
            created_at=kb.created_at.isoformat(),
            updated_at=kb.updated_at.isoformat(),
        )
