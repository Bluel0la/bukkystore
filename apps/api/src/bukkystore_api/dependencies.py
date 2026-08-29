from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from bukkystore_api.database import DatabaseProtocol


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    """Yield one request-scoped database session."""

    database: DatabaseProtocol = request.app.state.database
    async for session in database.session():
        yield session
