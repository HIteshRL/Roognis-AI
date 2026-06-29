from fastapi import APIRouter

from src.presentation.api.v1 import auth, chat, system, users

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(chat.router)
api_router.include_router(system.router)
