from __future__ import annotations

from fastapi import APIRouter

from app.admin.routes.dashboard import router as dashboard_router
from app.admin.routes.resources import router as resources_router


def build_admin_router() -> APIRouter:
    router = APIRouter()
    router.include_router(dashboard_router)
    router.include_router(resources_router)
    return router
