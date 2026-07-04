from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request

from src.application.dtos.school import (
    AddTeacherRequest,
    ClassroomResponse,
    CreateClassroomRequest,
    CreateSchoolRequest,
    CreateSyllabusItemRequest,
    JoinClassroomRequest,
    RosterEntryResponse,
    SchoolMemberResponse,
    SchoolResponse,
    SyllabusItemResponse,
    UpdateClassroomRequest,
    UpdateSyllabusItemRequest,
)
from src.application.dtos.user import UserResponse
from src.application.interfaces.dependencies import (
    get_classroom_analytics_service,
    get_classroom_service,
    get_current_user,
    get_school_service,
    get_syllabus_service,
    require_teacher,
)
from src.application.services.classroom_analytics_service import ClassroomAnalyticsService
from src.application.services.classroom_service import ClassroomService
from src.application.services.school_service import SchoolService
from src.application.services.syllabus_service import SyllabusService
from src.presentation.api.response import ok

router = APIRouter(prefix="/school", tags=["School & Classrooms"])


# ── Serializers ──────────────────────────────────────────────────────────────


def _school(s, my_role: str) -> dict:
    return SchoolResponse(
        id=str(s.id),
        name=s.name,
        slug=s.slug,
        address=s.address,
        is_active=s.is_active,
        my_role=my_role,
        created_at=s.created_at.isoformat(),
        updated_at=s.updated_at.isoformat(),
    ).model_dump(mode="json")


def _classroom(c, student_count: int = 0, syllabus_count: int = 0) -> dict:
    return ClassroomResponse(
        id=str(c.id),
        school_id=str(c.school_id),
        name=c.name,
        subject=c.subject,
        grade=c.grade,
        teacher_id=str(c.teacher_id) if c.teacher_id else None,
        join_code=c.join_code,
        description=c.description,
        is_active=c.is_active,
        student_count=student_count,
        syllabus_count=syllabus_count,
        created_at=c.created_at.isoformat(),
        updated_at=c.updated_at.isoformat(),
    ).model_dump(mode="json")


def _syllabus(i) -> dict:
    return SyllabusItemResponse(
        id=str(i.id),
        classroom_id=str(i.classroom_id),
        subject=i.subject,
        chapter=i.chapter,
        topic=i.topic,
        description=i.description,
        order_index=i.order_index,
        knowledge_base_id=str(i.knowledge_base_id) if i.knowledge_base_id else None,
        is_published=i.is_published,
        created_at=i.created_at.isoformat(),
        updated_at=i.updated_at.isoformat(),
    ).model_dump(mode="json")


# ── Schools (teacher / school-admin) ─────────────────────────────────────────


@router.post("/schools", response_model=None)
async def create_school(
    body: CreateSchoolRequest,
    request: Request,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    svc: Annotated[SchoolService, Depends(get_school_service)],
):
    school, my_role = await svc.create_school(
        owner_id=UUID(current_user.id), name=body.name, address=body.address
    )
    return ok(_school(school, my_role), request_id=request.state.request_id)


@router.get("/schools/mine", response_model=None)
async def my_schools(
    request: Request,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    svc: Annotated[SchoolService, Depends(get_school_service)],
):
    schools = await svc.list_my_schools(UUID(current_user.id))
    data = [_school(s, role) for s, role in schools]
    return ok(data, request_id=request.state.request_id)


@router.post("/schools/{school_id}/teachers", response_model=None)
async def add_teacher(
    school_id: str,
    body: AddTeacherRequest,
    request: Request,
    current_user: Annotated[UserResponse, Depends(require_teacher)],
    svc: Annotated[SchoolService, Depends(get_school_service)],
):
    member, email, username = await svc.add_teacher(
        school_id=UUID(school_id),
        actor_id=UUID(current_user.id),
        email=body.email,
        role=body.role,
    )
    data = SchoolMemberResponse(
        id=str(member.id),
        user_id=str(member.user_id),
        email=email,
        username=username,
        role=member.role,
        status=member.status,
    ).model_dump(mode="json")
    return ok(data, request_id=request.state.request_id)


@router.get("/schools/{school_id}/members", response_model=None)
async def school_members(
    school_id: str,
    request: Request,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    svc: Annotated[SchoolService, Depends(get_school_service)],
):
    members = await svc.list_members(UUID(school_id), UUID(current_user.id))
    data = [
        SchoolMemberResponse(
            id=str(m.id),
            user_id=str(m.user_id),
            email=email,
            username=username,
            role=m.role,
            status=m.status,
        ).model_dump(mode="json")
        for m, email, username in members
    ]
    return ok(data, request_id=request.state.request_id)


# ── Classrooms (teacher) ─────────────────────────────────────────────────────


@router.post("/classrooms", response_model=None)
async def create_classroom(
    body: CreateClassroomRequest,
    request: Request,
    current_user: Annotated[UserResponse, Depends(require_teacher)],
    svc: Annotated[ClassroomService, Depends(get_classroom_service)],
):
    classroom = await svc.create_classroom(
        teacher_id=UUID(current_user.id),
        school_id=UUID(body.school_id),
        name=body.name,
        subject=body.subject,
        grade=body.grade,
        description=body.description,
    )
    return ok(_classroom(classroom), request_id=request.state.request_id)


@router.get("/classrooms/mine", response_model=None)
async def my_classrooms(
    request: Request,
    current_user: Annotated[UserResponse, Depends(require_teacher)],
    svc: Annotated[ClassroomService, Depends(get_classroom_service)],
):
    classrooms = await svc.list_my_classrooms(UUID(current_user.id))
    data = []
    for c in classrooms:
        students, syllabus = await svc.counts(c.id)
        data.append(_classroom(c, students, syllabus))
    return ok(data, request_id=request.state.request_id)


@router.get("/classrooms/{classroom_id}", response_model=None)
async def get_classroom(
    classroom_id: str,
    request: Request,
    current_user: Annotated[UserResponse, Depends(require_teacher)],
    svc: Annotated[ClassroomService, Depends(get_classroom_service)],
):
    classroom = await svc.get_for_manage(UUID(classroom_id), UUID(current_user.id))
    students, syllabus = await svc.counts(classroom.id)
    return ok(_classroom(classroom, students, syllabus), request_id=request.state.request_id)


@router.patch("/classrooms/{classroom_id}", response_model=None)
async def update_classroom(
    classroom_id: str,
    body: UpdateClassroomRequest,
    request: Request,
    current_user: Annotated[UserResponse, Depends(require_teacher)],
    svc: Annotated[ClassroomService, Depends(get_classroom_service)],
):
    classroom = await svc.update_classroom(
        classroom_id=UUID(classroom_id),
        user_id=UUID(current_user.id),
        name=body.name,
        subject=body.subject,
        grade=body.grade,
        description=body.description,
        is_active=body.is_active,
    )
    return ok(_classroom(classroom), request_id=request.state.request_id)


@router.delete("/classrooms/{classroom_id}", response_model=None)
async def delete_classroom(
    classroom_id: str,
    request: Request,
    current_user: Annotated[UserResponse, Depends(require_teacher)],
    svc: Annotated[ClassroomService, Depends(get_classroom_service)],
):
    await svc.delete_classroom(UUID(classroom_id), UUID(current_user.id))
    return ok({"deleted": True}, request_id=request.state.request_id)


@router.get("/classrooms/{classroom_id}/roster", response_model=None)
async def classroom_roster(
    classroom_id: str,
    request: Request,
    current_user: Annotated[UserResponse, Depends(require_teacher)],
    svc: Annotated[ClassroomService, Depends(get_classroom_service)],
):
    roster = await svc.roster(UUID(classroom_id), UUID(current_user.id))
    data = [
        RosterEntryResponse(
            enrollment_id=str(e.id),
            student_id=str(e.student_id),
            username=username,
            email=email,
            status=e.status,
            enrolled_at=e.created_at.isoformat(),
        ).model_dump(mode="json")
        for e, username, email in roster
    ]
    return ok(data, request_id=request.state.request_id)


@router.get("/classrooms/{classroom_id}/analytics", response_model=None)
async def classroom_analytics(
    classroom_id: str,
    request: Request,
    current_user: Annotated[UserResponse, Depends(require_teacher)],
    svc: Annotated[ClassroomAnalyticsService, Depends(get_classroom_analytics_service)],
):
    data = await svc.classroom_analytics(UUID(classroom_id), UUID(current_user.id))
    return ok(data.model_dump(mode="json"), request_id=request.state.request_id)


# ── Syllabus (teacher writes, student reads published) ───────────────────────


@router.post("/classrooms/{classroom_id}/syllabus", response_model=None)
async def add_syllabus_item(
    classroom_id: str,
    body: CreateSyllabusItemRequest,
    request: Request,
    current_user: Annotated[UserResponse, Depends(require_teacher)],
    svc: Annotated[SyllabusService, Depends(get_syllabus_service)],
):
    item = await svc.add_item(
        classroom_id=UUID(classroom_id),
        user_id=UUID(current_user.id),
        subject=body.subject,
        chapter=body.chapter,
        topic=body.topic,
        description=body.description,
        order_index=body.order_index,
        knowledge_base_id=UUID(body.knowledge_base_id) if body.knowledge_base_id else None,
        is_published=body.is_published,
    )
    return ok(_syllabus(item), request_id=request.state.request_id)


@router.get("/classrooms/{classroom_id}/syllabus", response_model=None)
async def list_syllabus(
    classroom_id: str,
    request: Request,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    svc: Annotated[SyllabusService, Depends(get_syllabus_service)],
):
    items = await svc.list_items(UUID(classroom_id), UUID(current_user.id))
    return ok([_syllabus(i) for i in items], request_id=request.state.request_id)


@router.patch("/syllabus/{item_id}", response_model=None)
async def update_syllabus_item(
    item_id: str,
    body: UpdateSyllabusItemRequest,
    request: Request,
    current_user: Annotated[UserResponse, Depends(require_teacher)],
    svc: Annotated[SyllabusService, Depends(get_syllabus_service)],
):
    item = await svc.update_item(
        item_id=UUID(item_id),
        user_id=UUID(current_user.id),
        subject=body.subject,
        chapter=body.chapter,
        topic=body.topic,
        description=body.description,
        order_index=body.order_index,
        knowledge_base_id=(
            UUID(body.knowledge_base_id) if body.knowledge_base_id else None
        ),
        is_published=body.is_published,
    )
    return ok(_syllabus(item), request_id=request.state.request_id)


@router.delete("/syllabus/{item_id}", response_model=None)
async def delete_syllabus_item(
    item_id: str,
    request: Request,
    current_user: Annotated[UserResponse, Depends(require_teacher)],
    svc: Annotated[SyllabusService, Depends(get_syllabus_service)],
):
    await svc.delete_item(UUID(item_id), UUID(current_user.id))
    return ok({"deleted": True}, request_id=request.state.request_id)


# ── Student-facing ───────────────────────────────────────────────────────────


@router.post("/classrooms/join", response_model=None)
async def join_classroom(
    body: JoinClassroomRequest,
    request: Request,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    svc: Annotated[ClassroomService, Depends(get_classroom_service)],
):
    classroom = await svc.join_by_code(UUID(current_user.id), body.join_code)
    return ok(_classroom(classroom), request_id=request.state.request_id)


@router.get("/classrooms/enrolled/mine", response_model=None)
async def enrolled_classrooms(
    request: Request,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    svc: Annotated[ClassroomService, Depends(get_classroom_service)],
):
    classrooms = await svc.list_enrolled(UUID(current_user.id))
    data = []
    for c in classrooms:
        students, syllabus = await svc.counts(c.id)
        data.append(_classroom(c, students, syllabus))
    return ok(data, request_id=request.state.request_id)
