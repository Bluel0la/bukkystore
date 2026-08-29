from __future__ import annotations

import logging
import time
from uuid import UUID, uuid4

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from bukkystore_api.logging import correlation_id_context

logger = logging.getLogger(__name__)


def _safe_correlation_id(value: str | None) -> str:
    if value is None:
        return str(uuid4())
    try:
        return str(UUID(value))
    except ValueError:
        return str(uuid4())


class RequestContextMiddleware:
    """Attach a safe correlation ID and emit one bounded request metric log."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = {key.lower(): value for key, value in scope.get("headers", [])}
        raw_request_id = headers.get(b"x-request-id")
        correlation_id = _safe_correlation_id(
            raw_request_id.decode("ascii", errors="ignore") if raw_request_id else None
        )
        token = correlation_id_context.set(correlation_id)
        started = time.perf_counter()
        status_code = 500

        async def send_with_headers(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                response_headers = list(message.get("headers", []))
                response_headers.append((b"x-request-id", correlation_id.encode("ascii")))
                duration_ms = (time.perf_counter() - started) * 1000
                response_headers.append((b"server-timing", f"app;dur={duration_ms:.2f}".encode()))
                message["headers"] = response_headers
            await send(message)

        try:
            await self.app(scope, receive, send_with_headers)
        finally:
            duration_ms = (time.perf_counter() - started) * 1000
            logger.info(
                "http_request_completed",
                extra={
                    "method": scope.get("method"),
                    "path": scope.get("path"),
                    "status_code": status_code,
                    "duration_ms": round(duration_ms, 2),
                },
            )
            correlation_id_context.reset(token)
