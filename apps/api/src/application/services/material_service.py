"""
Classroom materials — folders (nested), any-file uploads, external links,
categories, rename/move, soft delete + restore, version history, bookmarks,
and per-student view/progress tracking.

Files are stored through the storage abstraction (local or S3-compatible);
nothing here assumes a filesystem.
"""
from uuid import UUID, uuid4

import structlog

from src.application.dtos.material import (
    CreateFolderRequest,
    CreateLinkMaterialRequest,
    FolderResponse,
    MaterialListResponse,
    MaterialResponse,
    MaterialVersionResponse,
    UpdateFolderRequest,
    UpdateMaterialRequest,
)
from src.domain.entities.lms import (
    MATERIAL_CATEGORIES,
    Bookmark,
    Folder,
    Material,
    MaterialVersion,
)
from src.domain.exceptions import AuthorizationError, EntityNotFound, ValidationError
from src.domain.repositories.classroom_repository import (
    AbstractClassroomRepository,
    AbstractEnrollmentRepository,
)
from src.domain.repositories.lms_repository import (
    AbstractBookmarkRepository,
    AbstractClassroomTeacherRepository,
    AbstractFolderRepository,
    AbstractMaterialRepository,
    AbstractMaterialViewRepository,
)

logger = structlog.get_logger(__name__)


class MaterialService:
    def __init__(
        self,
        material_repo: AbstractMaterialRepository,
        folder_repo: AbstractFolderRepository,
        classroom_repo: AbstractClassroomRepository,
        enrollment_repo: AbstractEnrollmentRepository,
        teacher_repo: AbstractClassroomTeacherRepository,
        bookmark_repo: AbstractBookmarkRepository,
        view_repo: AbstractMaterialViewRepository,
        storage,  # AbstractFileStorage
        notification_svc=None,  # NotificationService; fail-open emits
    ) -> None:
        self._materials = material_repo
        self._folders = folder_repo
        self._classrooms = classroom_repo
        self._enrollments = enrollment_repo
        self._teachers = teacher_repo
        self._bookmarks = bookmark_repo
        self._views = view_repo
        self._storage = storage
        self._notify = notification_svc

    # ── Folders ──────────────────────────────────────────────────────────────

    async def create_folder(
        self, teacher_id: UUID, classroom_id: UUID, dto: CreateFolderRequest
    ) -> FolderResponse:
        await self._assert_teaches(teacher_id, classroom_id)
        parent_id = None
        if dto.parent_id:
            parent = await self._folders.get_by_id(UUID(dto.parent_id))
            if not parent or parent.classroom_id != classroom_id or parent.is_deleted:
                raise EntityNotFound("Parent folder not found")
            parent_id = parent.id
        folder = await self._folders.create(
            Folder(classroom_id=classroom_id, name=dto.name, parent_id=parent_id)
        )
        return self._folder_to_response(folder)

    async def list_folders(
        self, user_id: UUID, classroom_id: UUID, as_teacher: bool
    ) -> list[FolderResponse]:
        if as_teacher:
            await self._assert_teaches(user_id, classroom_id)
        else:
            await self._assert_enrolled(user_id, classroom_id)
        folders = await self._folders.list_by_classroom(classroom_id)
        return [self._folder_to_response(f) for f in folders]

    async def update_folder(
        self, teacher_id: UUID, folder_id: UUID, dto: UpdateFolderRequest
    ) -> FolderResponse:
        folder = await self._get_folder(folder_id)
        await self._assert_teaches(teacher_id, folder.classroom_id)
        if dto.name is not None:
            folder.name = dto.name
        if dto.parent_id is not None:
            if dto.parent_id == "":
                folder.parent_id = None
            else:
                new_parent_id = UUID(dto.parent_id)
                if new_parent_id == folder.id:
                    raise ValidationError("A folder cannot be its own parent")
                parent = await self._folders.get_by_id(new_parent_id)
                if not parent or parent.classroom_id != folder.classroom_id or parent.is_deleted:
                    raise EntityNotFound("Parent folder not found")
                if await self._is_descendant(folder.classroom_id, parent.id, folder.id):
                    raise ValidationError("Cannot move a folder inside its own subtree")
                folder.parent_id = parent.id
        folder = await self._folders.update(folder)
        return self._folder_to_response(folder)

    async def delete_folder(self, teacher_id: UUID, folder_id: UUID) -> None:
        folder = await self._get_folder(folder_id)
        await self._assert_teaches(teacher_id, folder.classroom_id)
        folder.is_deleted = True
        from datetime import UTC, datetime

        folder.deleted_at = datetime.now(UTC)
        await self._folders.update(folder)

    async def restore_folder(self, teacher_id: UUID, folder_id: UUID) -> FolderResponse:
        folder = await self._folders.get_by_id(folder_id)
        if not folder:
            raise EntityNotFound("Folder not found")
        await self._assert_teaches(teacher_id, folder.classroom_id)
        folder.is_deleted = False
        folder.deleted_at = None
        folder = await self._folders.update(folder)
        return self._folder_to_response(folder)

    # ── Materials (teacher) ──────────────────────────────────────────────────

    async def upload_material(
        self,
        teacher_id: UUID,
        classroom_id: UUID,
        filename: str,
        file_bytes: bytes,
        content_type: str,
        title: str | None = None,
        description: str | None = None,
        category: str = "other",
        folder_id: UUID | None = None,
    ) -> MaterialResponse:
        classroom = await self._assert_teaches(teacher_id, classroom_id)
        if category not in MATERIAL_CATEGORIES:
            raise ValidationError(f"Unknown category '{category}'")
        if folder_id:
            folder = await self._folders.get_by_id(folder_id)
            if not folder or folder.classroom_id != classroom_id or folder.is_deleted:
                raise EntityNotFound("Folder not found")

        material = Material(
            classroom_id=classroom_id,
            uploaded_by=teacher_id,
            title=title or filename,
            description=description,
            category=category,
            folder_id=folder_id,
            filename=filename,
            file_type=content_type or _guess_type(filename),
            file_size=len(file_bytes),
        )
        material.storage_path = await self._storage.save(
            file_bytes, self._path_for(material, version=1)
        )
        material = await self._materials.create(material)
        await self._materials.add_version(
            MaterialVersion(
                material_id=material.id,
                version=1,
                filename=filename,
                file_size=len(file_bytes),
                storage_path=material.storage_path,
                uploaded_by=teacher_id,
            )
        )
        await self._notify_students(
            classroom_id,
            type="new_material",
            title=f"New material in {classroom.name}: {material.title}",
            data={"classroom_id": str(classroom_id), "material_id": str(material.id)},
        )
        logger.info("material_uploaded", material_id=str(material.id), size=len(file_bytes))
        return self._material_to_response(material)

    async def upload_new_version(
        self,
        teacher_id: UUID,
        material_id: UUID,
        filename: str,
        file_bytes: bytes,
        content_type: str,
    ) -> MaterialResponse:
        material = await self._get_material(material_id)
        await self._assert_teaches(teacher_id, material.classroom_id)
        if material.link_url:
            raise ValidationError("Link materials have no file versions")
        material.version += 1
        material.filename = filename
        material.file_type = content_type or _guess_type(filename)
        material.file_size = len(file_bytes)
        material.storage_path = await self._storage.save(
            file_bytes, self._path_for(material, version=material.version)
        )
        material = await self._materials.update(material)
        await self._materials.add_version(
            MaterialVersion(
                material_id=material.id,
                version=material.version,
                filename=filename,
                file_size=len(file_bytes),
                storage_path=material.storage_path,
                uploaded_by=teacher_id,
            )
        )
        return self._material_to_response(material)

    async def create_link_material(
        self, teacher_id: UUID, classroom_id: UUID, dto: CreateLinkMaterialRequest
    ) -> MaterialResponse:
        classroom = await self._assert_teaches(teacher_id, classroom_id)
        material = await self._materials.create(
            Material(
                classroom_id=classroom_id,
                uploaded_by=teacher_id,
                title=dto.title,
                description=dto.description,
                category=dto.category,
                folder_id=UUID(dto.folder_id) if dto.folder_id else None,
                link_url=dto.link_url,
            )
        )
        await self._notify_students(
            classroom_id,
            type="new_material",
            title=f"New material in {classroom.name}: {material.title}",
            data={"classroom_id": str(classroom_id), "material_id": str(material.id)},
        )
        return self._material_to_response(material)

    async def update_material(
        self, teacher_id: UUID, material_id: UUID, dto: UpdateMaterialRequest
    ) -> MaterialResponse:
        material = await self._get_material(material_id)
        await self._assert_teaches(teacher_id, material.classroom_id)
        if dto.title is not None:
            material.title = dto.title
        if dto.description is not None:
            material.description = dto.description
        if dto.category is not None:
            material.category = dto.category
        material = await self._materials.update(material)
        return self._material_to_response(material)

    async def move_material(
        self, teacher_id: UUID, material_id: UUID, folder_id: UUID | None
    ) -> MaterialResponse:
        material = await self._get_material(material_id)
        await self._assert_teaches(teacher_id, material.classroom_id)
        if folder_id:
            folder = await self._folders.get_by_id(folder_id)
            if not folder or folder.classroom_id != material.classroom_id or folder.is_deleted:
                raise EntityNotFound("Folder not found")
        material.folder_id = folder_id
        material = await self._materials.update(material)
        return self._material_to_response(material)

    async def delete_material(self, teacher_id: UUID, material_id: UUID) -> None:
        material = await self._get_material(material_id)
        await self._assert_teaches(teacher_id, material.classroom_id)
        material.soft_delete()
        await self._materials.update(material)

    async def restore_material(self, teacher_id: UUID, material_id: UUID) -> MaterialResponse:
        material = await self._materials.get_by_id(material_id)
        if not material:
            raise EntityNotFound("Material not found")
        await self._assert_teaches(teacher_id, material.classroom_id)
        material.restore()
        material = await self._materials.update(material)
        return self._material_to_response(material)

    async def purge_material(self, teacher_id: UUID, material_id: UUID) -> None:
        """Hard delete from trash — removes stored files for every version."""
        material = await self._materials.get_by_id(material_id)
        if not material:
            raise EntityNotFound("Material not found")
        await self._assert_teaches(teacher_id, material.classroom_id)
        if not material.is_deleted:
            raise ValidationError("Material must be in trash before permanent deletion")
        for version in await self._materials.list_versions(material_id):
            if version.storage_path:
                try:
                    await self._storage.delete(version.storage_path)
                except Exception as exc:
                    logger.warning("material_file_delete_failed", error=str(exc))
        await self._materials.delete(material_id)

    async def list_versions(
        self, teacher_id: UUID, material_id: UUID
    ) -> list[MaterialVersionResponse]:
        material = await self._get_material(material_id)
        await self._assert_teaches(teacher_id, material.classroom_id)
        versions = await self._materials.list_versions(material_id)
        return [
            MaterialVersionResponse(
                id=str(v.id),
                version=v.version,
                filename=v.filename,
                file_size=v.file_size,
                uploaded_by=str(v.uploaded_by) if v.uploaded_by else None,
                created_at=v.created_at.isoformat(),
            )
            for v in versions
        ]

    async def list_trash(
        self, teacher_id: UUID, classroom_id: UUID, page: int = 1, limit: int = 50
    ) -> MaterialListResponse:
        await self._assert_teaches(teacher_id, classroom_id)
        items, total = await self._materials.list_by_classroom(
            classroom_id, only_deleted=True, include_deleted=True, page=page, limit=limit
        )
        return MaterialListResponse(
            items=[self._material_to_response(m) for m in items],
            total=total,
            page=page,
            limit=limit,
        )

    # ── Listing & download (teacher + student) ───────────────────────────────

    async def list_materials(
        self,
        user_id: UUID,
        classroom_id: UUID,
        as_teacher: bool,
        folder_id: UUID | None = None,
        category: str | None = None,
        search: str | None = None,
        page: int = 1,
        limit: int = 50,
        sort: str = "created_at",
        descending: bool = True,
    ) -> MaterialListResponse:
        if as_teacher:
            await self._assert_teaches(user_id, classroom_id)
        else:
            await self._assert_enrolled(user_id, classroom_id)
        items, total = await self._materials.list_by_classroom(
            classroom_id,
            folder_id=folder_id,
            category=category,
            search=search,
            page=page,
            limit=limit,
            sort=sort,
            descending=descending,
        )
        bookmarked: set[UUID] = set()
        if not as_teacher and items:
            bookmarked = set(await self._bookmarks.list_material_ids(user_id))
        return MaterialListResponse(
            items=[
                self._material_to_response(m, is_bookmarked=m.id in bookmarked) for m in items
            ],
            total=total,
            page=page,
            limit=limit,
        )

    async def download(
        self, user_id: UUID, material_id: UUID, as_teacher: bool
    ) -> tuple[Material, bytes]:
        material = await self._get_material(material_id)
        if as_teacher:
            await self._assert_teaches(user_id, material.classroom_id)
        else:
            await self._assert_enrolled(user_id, material.classroom_id)
        if not material.storage_path:
            raise ValidationError("This material is an external link — nothing to download")
        data = await self._storage.read(material.storage_path)
        await self._materials.increment_downloads(material_id)
        if not as_teacher and self._notify:
            await self._notify.emit(
                user_id=material.uploaded_by,
                type="material_downloaded",
                title=f"Your material '{material.title}' was downloaded",
                data={"material_id": str(material_id)},
            )
        return material, data

    # ── Student material state ───────────────────────────────────────────────

    async def bookmark(self, student_id: UUID, material_id: UUID) -> None:
        material = await self._get_material(material_id)
        await self._assert_enrolled(student_id, material.classroom_id)
        if not await self._bookmarks.exists(student_id, material_id):
            await self._bookmarks.add(Bookmark(user_id=student_id, material_id=material_id))

    async def unbookmark(self, student_id: UUID, material_id: UUID) -> None:
        await self._bookmarks.remove(student_id, material_id)

    async def list_bookmarks(self, student_id: UUID) -> list[MaterialResponse]:
        out: list[MaterialResponse] = []
        for material_id in await self._bookmarks.list_material_ids(student_id):
            material = await self._materials.get_by_id(material_id)
            if material and not material.is_deleted:
                out.append(self._material_to_response(material, is_bookmarked=True))
        return out

    async def record_view(
        self, student_id: UUID, material_id: UUID, progress: float | None = None
    ) -> None:
        material = await self._get_material(material_id)
        await self._assert_enrolled(student_id, material.classroom_id)
        await self._views.record_view(student_id, material_id, progress)

    async def recently_viewed(self, student_id: UUID, limit: int = 10) -> list[MaterialResponse]:
        return await self._views_to_materials(
            await self._views.list_recent(student_id, limit=limit)
        )

    async def continue_reading(self, student_id: UUID, limit: int = 10) -> list[MaterialResponse]:
        return await self._views_to_materials(
            await self._views.list_in_progress(student_id, limit=limit)
        )

    # ── Helpers ──────────────────────────────────────────────────────────────

    async def _views_to_materials(self, views) -> list[MaterialResponse]:
        out: list[MaterialResponse] = []
        for view in views:
            material = await self._materials.get_by_id(view.material_id)
            if material and not material.is_deleted:
                out.append(self._material_to_response(material, progress=view.progress))
        return out

    async def _assert_teaches(self, teacher_id: UUID, classroom_id: UUID):
        classroom = await self._classrooms.get_by_id(classroom_id)
        if not classroom or classroom.is_deleted:
            raise EntityNotFound("Classroom not found")
        if classroom.teacher_id == teacher_id:
            return classroom
        if await self._teachers.get(classroom_id, teacher_id):
            return classroom
        raise AuthorizationError("You do not teach this classroom")

    async def _assert_enrolled(self, student_id: UUID, classroom_id: UUID) -> None:
        if not await self._enrollments.is_enrolled(classroom_id, student_id):
            raise AuthorizationError("You are not enrolled in this class")

    async def _get_material(self, material_id: UUID) -> Material:
        material = await self._materials.get_by_id(material_id)
        if not material or material.is_deleted:
            raise EntityNotFound("Material not found")
        return material

    async def _get_folder(self, folder_id: UUID) -> Folder:
        folder = await self._folders.get_by_id(folder_id)
        if not folder or folder.is_deleted:
            raise EntityNotFound("Folder not found")
        return folder

    async def _is_descendant(
        self, classroom_id: UUID, candidate: UUID, ancestor: UUID
    ) -> bool:
        """True if `candidate` sits anywhere under `ancestor` in the folder tree."""
        current = candidate
        for _ in range(64):  # cycle guard
            folder = await self._folders.get_by_id(current)
            if not folder or folder.parent_id is None:
                return False
            if folder.parent_id == ancestor:
                return True
            current = folder.parent_id
        return True

    async def _notify_students(self, classroom_id: UUID, type: str, title: str, data: dict) -> None:
        if not self._notify:
            return
        students = await self._enrollments.list_students(classroom_id)
        await self._notify.emit_many([s.id for s in students], type=type, title=title, data=data)

    def _path_for(self, material: Material, version: int) -> str:
        safe_name = (material.filename or "file").replace("/", "_").replace("\\", "_")
        return (
            f"lms/{material.classroom_id}/materials/{material.id}/v{version}/"
            f"{uuid4().hex[:8]}_{safe_name}"
        )

    @staticmethod
    def _folder_to_response(f: Folder) -> FolderResponse:
        return FolderResponse(
            id=str(f.id),
            classroom_id=str(f.classroom_id),
            parent_id=str(f.parent_id) if f.parent_id else None,
            name=f.name,
            is_deleted=f.is_deleted,
            created_at=f.created_at.isoformat(),
            updated_at=f.updated_at.isoformat(),
        )

    @staticmethod
    def _material_to_response(
        m: Material, is_bookmarked: bool = False, progress: float | None = None
    ) -> MaterialResponse:
        return MaterialResponse(
            id=str(m.id),
            classroom_id=str(m.classroom_id),
            folder_id=str(m.folder_id) if m.folder_id else None,
            uploaded_by=str(m.uploaded_by),
            title=m.title,
            description=m.description,
            category=m.category,
            filename=m.filename,
            file_type=m.file_type,
            file_size=m.file_size,
            link_url=m.link_url,
            version=m.version,
            download_count=m.download_count,
            is_deleted=m.is_deleted,
            is_bookmarked=is_bookmarked,
            progress=progress,
            created_at=m.created_at.isoformat(),
            updated_at=m.updated_at.isoformat(),
        )


def _guess_type(filename: str) -> str:
    import mimetypes

    guessed, _ = mimetypes.guess_type(filename)
    return guessed or "application/octet-stream"
