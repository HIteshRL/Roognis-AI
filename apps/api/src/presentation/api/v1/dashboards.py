"""Dashboard endpoints — teacher classroom analytics + student home."""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request

from src.application.dtos.user import UserResponse
from src.application.interfaces.dependencies import (
    get_current_user,
    get_student_dashboard_service,
    get_teacher_analytics_service,
    require_teacher,
)
from src.application.services.student_dashboard_service import StudentDashboardService
from src.application.services.teacher_analytics_service import TeacherAnalyticsService
from src.presentation.api.response import ok

teacher_router = APIRouter(prefix="/teacher", tags=["Analytics (Teacher)"])
student_router = APIRouter(prefix="/student", tags=["Dashboard (Student)"])


@teacher_router.get("/classrooms/{classroom_id}/analytics")
async def classroom_analytics(
    classroom_id: UUID,
    request: Request,
    teacher: Annotated[UserResponse, Depends(require_teacher)],
    svc: Annotated[TeacherAnalyticsService, Depends(get_teacher_analytics_service)],
):
    result = await svc.dashboard(UUID(teacher.id), classroom_id)
    return ok(result, request_id=request.state.request_id)


@student_router.get("/dashboard")
async def student_dashboard(
    request: Request,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    svc: Annotated[StudentDashboardService, Depends(get_student_dashboard_service)],
):
    result = await svc.dashboard(UUID(current_user.id))
    return ok(result, request_id=request.state.request_id)
