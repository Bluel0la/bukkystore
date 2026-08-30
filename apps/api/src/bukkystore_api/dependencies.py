from __future__ import annotations

from collections.abc import AsyncIterator
from typing import cast

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from bukkystore_api.config import Settings
from bukkystore_api.database import DatabaseProtocol


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    """Yield one request-scoped database session."""

    database: DatabaseProtocol = request.app.state.database
    async for session in database.session():
        yield session


def get_app_settings(request: Request) -> Settings:
    """Return the validated settings attached during application startup."""

    return cast(Settings, request.app.state.settings)
