from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from kdmp_api.core.config import Settings, get_settings
from kdmp_api.core.database import build_engine
from kdmp_api.core.observability import RequestContextMiddleware, configure_logging, logger
from kdmp_api.modules.cooperatives.router import router as cooperatives_router
from kdmp_api.modules.health.router import router as health_router


def create_app(settings: Settings | None = None) -> FastAPI:
    config = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        configure_logging()
        app.state.engine = build_engine(config)
        try:
            yield
        finally:
            app.state.engine.dispose()

    app = FastAPI(
        title="Merah Putih WebGIS API",
        version="0.1.0",
        description="Public, bounded geospatial reads. No administrative writes in this phase.",
        lifespan=lifespan,
        docs_url="/docs" if config.environment != "production" else None,
        redoc_url=None,
        openapi_url="/openapi.json" if config.environment != "production" else None,
    )
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=config.allowed_hosts)
    if config.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=config.cors_origins,
            allow_credentials=False,
            allow_methods=["GET"],
            allow_headers=["X-Request-ID"],
            expose_headers=["X-Request-ID"],
        )
    app.add_middleware(RequestContextMiddleware)

    @app.exception_handler(SQLAlchemyError)
    async def database_error(request: Request, exc: SQLAlchemyError) -> JSONResponse:
        logger.error(
            "database_unavailable",
            extra={
                "context": {
                    "request_id": request.state.request_id,
                    "error_type": type(exc).__name__,
                }
            },
        )
        return JSONResponse(
            status_code=503, content={"detail": "Data service temporarily unavailable"}
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        # Do not echo arbitrary user input, raw SQL, or Python validation context.
        errors = [
            {"loc": list(error["loc"]), "msg": error["msg"], "type": error["type"]}
            for error in exc.errors()
        ]
        return JSONResponse(status_code=422, content={"detail": errors})

    app.include_router(health_router)
    app.include_router(cooperatives_router, prefix="/api/v1")
    return app
