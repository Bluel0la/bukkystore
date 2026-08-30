from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from bukkystore_api.admin_analytics.router import router as admin_analytics_router
from bukkystore_api.admin_catalogue.router import router as admin_catalogue_router
from bukkystore_api.admin_orders.router import router as admin_orders_router
from bukkystore_api.api import router
from bukkystore_api.auth.router import router as auth_router
from bukkystore_api.catalogue.router import router as catalogue_router
from bukkystore_api.commerce.payments import PaymentProvider, build_payment_provider
from bukkystore_api.commerce.router import router as commerce_router
from bukkystore_api.config import Settings, get_settings
from bukkystore_api.database import Database, DatabaseProtocol
from bukkystore_api.errors import ApiError
from bukkystore_api.logging import configure_logging, correlation_id_context
from bukkystore_api.middleware import RequestContextMiddleware
from bukkystore_api.schemas import ErrorResponse

logger = logging.getLogger(__name__)


def create_app(
    settings: Settings | None = None,
    database: DatabaseProtocol | None = None,
    payment_provider: PaymentProvider | None = None,
) -> FastAPI:
    resolved_settings = settings or get_settings()
    configure_logging(resolved_settings.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.settings = resolved_settings
        app.state.database = database or Database(str(resolved_settings.database_url))
        app.state.payment_provider = payment_provider or build_payment_provider(
            resolved_settings.payment_provider, str(resolved_settings.public_site_url)
        )
        logger.info("application_started", extra={"environment": resolved_settings.environment})
        try:
            yield
        finally:
            await app.state.database.dispose()
            logger.info("application_stopped")

    app = FastAPI(
        title="Bukky Store API",
        summary="Authoritative commerce API for the Bukky Store storefront and admin.",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/api/docs" if resolved_settings.environment != "production" else None,
        redoc_url=None,
        openapi_url="/api/openapi.json",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin).rstrip("/") for origin in resolved_settings.cors_origins],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Idempotency-Key", "X-CSRF-Token", "X-Request-ID"],
    )
    app.add_middleware(RequestContextMiddleware)
    app.include_router(router)
    app.include_router(catalogue_router)
    app.include_router(auth_router)
    app.include_router(admin_catalogue_router)
    app.include_router(admin_analytics_router)
    app.include_router(admin_orders_router)
    app.include_router(commerce_router)

    @app.exception_handler(ApiError)
    async def api_error_handler(_request: Request, exc: ApiError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                code=exc.code,
                message=exc.message,
                correlation_id=correlation_id_context.get() or "unknown",
            ).model_dump(),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        _request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        safe_errors = [
            {"location": list(error["loc"]), "message": error["msg"], "type": error["type"]}
            for error in exc.errors()
        ]
        return JSONResponse(
            status_code=422,
            content={
                "code": "validation_failed",
                "message": "The request could not be validated.",
                "correlation_id": correlation_id_context.get() or "unknown",
                "details": safe_errors,
            },
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_error_handler(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
        messages = {
            400: "The request body could not be parsed.",
            404: "The requested resource was not found.",
            405: "The request method is not allowed.",
        }
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                code=f"http_{exc.status_code}",
                message=messages.get(exc.status_code, "The request could not be completed."),
                correlation_id=correlation_id_context.get() or "unknown",
            ).model_dump(),
            headers=exc.headers,
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(_request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled_request_error", exc_info=exc)
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                code="internal_error",
                message="An unexpected error occurred.",
                correlation_id=correlation_id_context.get() or "unknown",
            ).model_dump(),
        )

    return app
