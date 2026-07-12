from fastapi import APIRouter

from src.presentation.api.v1 import (
    admin,
    auth,
    chat,
    coursework,
    dashboards,
    discussions,
    documents,
    enrollment,
    library,
    materials,
    notifications,
    questions,
    rag,
    search,
    student,
    submissions,
    system,
    teacher,
    users,
)

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(chat.router)
api_router.include_router(library.router)
api_router.include_router(documents.router)
api_router.include_router(search.router)
api_router.include_router(rag.router)
api_router.include_router(student.router)
api_router.include_router(questions.router)
api_router.include_router(teacher.router)
api_router.include_router(enrollment.router)
api_router.include_router(materials.teacher_router)
api_router.include_router(materials.student_router)
api_router.include_router(coursework.teacher_router)
api_router.include_router(coursework.student_router)
api_router.include_router(submissions.teacher_router)
api_router.include_router(submissions.student_router)
api_router.include_router(discussions.router)
api_router.include_router(dashboards.teacher_router)
api_router.include_router(dashboards.student_router)
api_router.include_router(notifications.router)
api_router.include_router(admin.router)
api_router.include_router(system.router)
