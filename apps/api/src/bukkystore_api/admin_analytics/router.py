from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from bukkystore_api.admin_analytics.schemas import AdminAnalyticsOverview, AnalyticsRangeQuery
from bukkystore_api.admin_analytics.service import get_admin_analytics_overview
from bukkystore_api.auth.dependencies import AdminContext, require_admin
from bukkystore_api.dependencies import get_session
from bukkystore_api.schemas import ErrorResponse

router = APIRouter(
    prefix="/api/v1/admin/analytics",
    tags=["Admin analytics"],
    responses={401: {"model": ErrorResponse, "description": "Administrator sign-in is required."}},
)
Session = Annotated[AsyncSession, Depends(get_session)]
Authenticated = Annotated[AdminContext, Depends(require_admin)]


@router.get(
    "/overview",
    response_model=AdminAnalyticsOverview,
    summary="Get store operations overview",
)
async def analytics_overview(
    session: Session,
    _admin: Authenticated,
    query: Annotated[AnalyticsRangeQuery, Query()],
) -> AdminAnalyticsOverview:
    """Return bounded sales, fulfilment, inventory, product, and source metrics."""

    return await get_admin_analytics_overview(session, query)
