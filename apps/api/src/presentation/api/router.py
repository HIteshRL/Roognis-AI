from fastapi import APIRouter

from src.presentation.api.v1 import admin, auth, chat, documents, library, search, system, users

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(chat.router)
api_router.include_router(library.router)
api_router.include_router(documents.router)
api_router.include_router(search.router)
api_router.include_router(admin.router)
api_router.include_router(system.router)
