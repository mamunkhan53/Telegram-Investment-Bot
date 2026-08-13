from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.admin.admin import build_admin_router
from app.config.settings import get_settings
from app.database.session import check_database_connection, dispose_engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.settings = get_settings()
    yield
    await dispose_engine()


app = FastAPI(
    title="Telegram Investment Platform API", version="0.1.0", lifespan=lifespan
)
app.include_router(build_admin_router())


@app.get("/healthz", tags=["system"])
async def healthz() -> dict[str, str]:
    database = await check_database_connection()
    return {
        "status": "ok" if database else "degraded",
        "database": "ok" if database else "unavailable",
    }


@app.get("/readyz", tags=["system"])
async def readyz() -> dict[str, str]:
    if not await check_database_connection():
        return {"status": "not_ready"}
    return {"status": "ready"}
