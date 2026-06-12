import logging
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.api.router import api_router
from app.core.bootstrap import ensure_default_roles, ensure_first_super_admin
from app.core.config import get_settings
from app.core.database import Base, SessionLocal, engine

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("ecommerce-api")


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    if settings.create_tables_on_startup:
        Base.metadata.create_all(bind=engine)
        with SessionLocal() as db:
            ensure_default_roles(db)
            ensure_first_super_admin(db)
    elif settings.first_super_admin_email and settings.first_super_admin_password:
        with SessionLocal() as db:
            ensure_default_roles(db)
            ensure_first_super_admin(db)
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version="1.0.0",
        description="Production-style multi-vendor e-commerce backend built with FastAPI and SQLAlchemy.",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        started_at = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - started_at) * 1000
        logger.info("%s %s %s %.2fms", request.method, request.url.path, response.status_code, duration_ms)
        return response

    @app.exception_handler(IntegrityError)
    async def integrity_error_handler(_: Request, exc: IntegrityError):
        logger.warning("Database integrity error: %s", exc)
        return JSONResponse(status_code=409, content={"detail": "Duplicate or invalid related data"})

    @app.exception_handler(SQLAlchemyError)
    async def database_error_handler(_: Request, exc: SQLAlchemyError):
        logger.exception("Database error: %s", exc)
        return JSONResponse(status_code=500, content={"detail": "Database error"})

    @app.get("/health", tags=["Health"])
    def health_check() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(api_router)
    return app


app = create_app()
