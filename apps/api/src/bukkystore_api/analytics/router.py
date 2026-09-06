from __future__ import annotations

import time
from collections import defaultdict, deque
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from bukkystore_api.analytics.schemas import AnalyticsEventCreate, AnalyticsEventResponse
from bukkystore_api.analytics.service import record_event
from bukkystore_api.dependencies import get_session
from bukkystore_api.errors import ApiError
from bukkystore_api.schemas import ErrorResponse

router = APIRouter(prefix="/api/v1", tags=["Analytics"])
Session = Annotated[AsyncSession, Depends(get_session)]

RATE_LIMIT_REQUESTS = 30
RATE_LIMIT_WINDOW_SECONDS = 60.0

# Single-instance sliding window. The store runs one API process, so an
# in-process limiter is sufficient; revisit if the API scales horizontally.
_request_times: dict[str, deque[float]] = defaultdict(deque)


def reset_rate_limiter() -> None:
    """Clear tracked request times. Used by tests to isolate rate-limit cases."""

    _request_times.clear()


def check_rate_limit(client_id: str, *, now: float | None = None) -> None:
    """Raise a 429 when a client exceeds the ingestion rate budget."""

    current = now if now is not None else time.monotonic()
    window_start = current - RATE_LIMIT_WINDOW_SECONDS
    recent = _request_times[client_id]
    while recent and recent[0] <= window_start:
        recent.popleft()
    if len(recent) >= RATE_LIMIT_REQUESTS:
        raise ApiError(429, "rate_limited", "Too many analytics events. Please try again shortly.")
    recent.append(current)


@router.post(
    "/analytics/events",
    response_model=AnalyticsEventResponse,
    status_code=201,
    responses={
        404: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
    },
    summary="Record a storefront analytics event",
)
async def analytics_event(
    payload: AnalyticsEventCreate, session: Session, request: Request
) -> AnalyticsEventResponse:
    """Accept one best-effort event. Analytics failures never affect commerce.

    Source and campaign are normalized (trimmed, lowercased, defaulted to
    "direct"), so schema-edge values around whitespace or casing may be
    accepted after normalization rather than rejected.
    """

    forwarded = request.headers.get("x-forwarded-for")
    client_id = forwarded.split(",")[0].strip() if forwarded else None
    if not client_id:
        client_id = request.client.host if request.client else "unknown"
    check_rate_limit(client_id)
    return await record_event(session, payload)
