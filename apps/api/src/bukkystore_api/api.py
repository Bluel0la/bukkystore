from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from bukkystore_api import __version__
from bukkystore_api.logging import correlation_id_context
from bukkystore_api.schemas import ErrorResponse, HealthResponse, ReadinessResponse

router = APIRouter(prefix="/api/v1")


@router.get(
    "/health/live",
    response_model=HealthResponse,
    summary="Check process liveness",
    tags=["System"],
)
async def liveness() -> HealthResponse:
    """Return success when the API process can serve requests."""

    return HealthResponse(status="ok", version=__version__)


@router.get(
    "/health/ready",
    response_model=ReadinessResponse,
    responses={503: {"model": ErrorResponse}},
    summary="Check dependency readiness",
    tags=["System"],
)
async def readiness(request: Request) -> ReadinessResponse | JSONResponse:
    """Return success only when required infrastructure is reachable."""

    try:
        await request.app.state.database.is_ready()
    except (SQLAlchemyError, OSError):
        return JSONResponse(
            status_code=503,
            content=ErrorResponse(
                code="service_not_ready",
                message="A required service is unavailable.",
                correlation_id=correlation_id_context.get() or "unknown",
            ).model_dump(),
        )
    return ReadinessResponse(status="ready", database="available")
