from uuid import UUID

import structlog

from src.application.services.classroom_service import ClassroomService
from src.application.services.document_service import DocumentService
from src.domain.entities.knowledge import Document, IngestionJob, KnowledgeBase
from src.domain.entities.school import Classroom
from src.domain.repositories.knowledge_repository import AbstractKnowledgeBaseRepository
from src.domain.repositories.school_repository import AbstractClassroomRepository

logger = structlog.get_logger(__name__)


class ClassroomMaterialsService:
    """
    Teacher content bridge. A teacher uploads a file to a classroom; it is
    ingested into that classroom's own knowledge base (lazily created on first
    upload) and, via retrieval scoping, grounds the enrolled students' AI tutor.

    Authorization and classroom access are delegated to ClassroomService so the
    "who may manage this class" rule lives in exactly one place.
    """

    def __init__(
        self,
        classroom_service: ClassroomService,
        classroom_repo: AbstractClassroomRepository,
        kb_repo: AbstractKnowledgeBaseRepository,
        document_svc: DocumentService,
    ) -> None:
        self._classrooms_svc = classroom_service
        self._classrooms = classroom_repo
        self._kbs = kb_repo
        self._docs = document_svc

    async def ensure_kb(self, classroom: Classroom, owner_id: UUID) -> UUID:
        """Return the classroom's KB id, creating one on first use."""
        if classroom.knowledge_base_id:
            return classroom.knowledge_base_id

        kb = await self._kbs.create(
            KnowledgeBase(
                name=f"Class — {classroom.name}",
                created_by=owner_id,
                subject=classroom.subject,
                grade=classroom.grade,
                description=f"Teacher-uploaded materials for {classroom.name}.",
            )
        )
        classroom.knowledge_base_id = kb.id
        await self._classrooms.update(classroom)
        logger.info(
            "classroom_kb_created",
            classroom_id=str(classroom.id),
            knowledge_base_id=str(kb.id),
        )
        return kb.id

    async def upload_material(
        self,
        classroom_id: UUID,
        teacher_id: UUID,
        filename: str,
        file_bytes: bytes,
        content_type: str,
        chapter: str | None = None,
    ) -> tuple[Document, IngestionJob]:
        classroom = await self._classrooms_svc.get_for_manage(classroom_id, teacher_id)
        kb_id = await self.ensure_kb(classroom, teacher_id)

        title = filename
        doc, job = await self._docs.upload(
            kb_id=kb_id,
            user_id=teacher_id,
            filename=filename,
            file_bytes=file_bytes,
            content_type=content_type,
            title=title,
            description=chapter,
        )
        if chapter:
            doc.metadata = {**(doc.metadata or {}), "chapter": chapter}
        logger.info(
            "classroom_material_uploaded",
            classroom_id=str(classroom_id),
            document_id=str(doc.id),
        )
        return doc, job

    async def list_materials(self, classroom_id: UUID, user_id: UUID) -> list[Document]:
        classroom = await self._classrooms_svc.get_for_manage(classroom_id, user_id)
        if not classroom.knowledge_base_id:
            return []
        docs, _ = await self._docs.list_documents(
            classroom.knowledge_base_id, page=1, limit=200
        )
        return docs

    async def count_materials(self, classroom: Classroom) -> int:
        """Material count for an already-authorized classroom (no re-auth)."""
        if not classroom.knowledge_base_id:
            return 0
        _, total = await self._docs.list_documents(
            classroom.knowledge_base_id, page=1, limit=1
        )
        return total

    async def delete_material(
        self, classroom_id: UUID, teacher_id: UUID, document_id: UUID
    ) -> None:
        await self._classrooms_svc.get_for_manage(classroom_id, teacher_id)
        await self._docs.delete_document(document_id, teacher_id)
