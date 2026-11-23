import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.config import get_settings
from app.database import Base, SessionLocal, engine
from app.routers import admin, auth, catalog, pages, reservations, users
from app.services.users import ensure_admin

logger = logging.getLogger("aidhub")
INIT_LOCK_KEY = 727_001


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    # Для MVP схема створюється при старті. У наступних роботах — Alembic.
    # Кілька реплік стартують одночасно, тому в PostgreSQL ініціалізація
    # серіалізується advisory-локом (інакше можлива гонка CREATE TABLE).
    with engine.connect() as lock_conn:
        is_pg = engine.dialect.name == "postgresql"
        if is_pg:
            lock_conn.execute(text("SELECT pg_advisory_lock(:key)"), {"key": INIT_LOCK_KEY})
        try:
            Base.metadata.create_all(engine)
            with SessionLocal() as db:
                ensure_admin(db, get_settings())
        finally:
            if is_pg:
                lock_conn.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": INIT_LOCK_KEY})
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="AidHub",
        version="0.1.0",
        debug=settings.debug,
        # Swagger і схема доступні лише поза production-режимом із DEBUG.
        docs_url="/docs" if settings.debug else None,
        redoc_url=None,
        openapi_url="/openapi.json" if settings.debug else None,
        lifespan=lifespan,
    )

    api = APIRouter(prefix="/api/v1")
    for module in (auth, users, admin, catalog, reservations):
        api.include_router(module.router)
    app.include_router(api)
    app.include_router(pages.router)

    @app.exception_handler(Exception)
    async def unhandled_error(request: Request, exc: Exception) -> JSONResponse:
        # Стектрейс — лише в лог; клієнт бачить загальне повідомлення.
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse({"detail": "Internal server error"}, status_code=500)

    @app.middleware("http")
    async def add_instance_header(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Instance"] = pages.INSTANCE
        return response

    return app


app = create_app()
