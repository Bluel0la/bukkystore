from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TypedDict
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from bukkystore_api.analytics.models import AnalyticsEvent, AnalyticsEventType
from bukkystore_api.analytics.schemas import (
    AnalyticsEventCreate,
    AnalyticsEventResponse,
)
from bukkystore_api.catalogue.models import Product
from bukkystore_api.errors import ApiError

logger = logging.getLogger(__name__)


class ProductEngagement(TypedDict):
    product_id: UUID
    product_name: str
    views: int
    whatsapp_clicks: int


async def record_event(
    session: AsyncSession, payload: AnalyticsEventCreate
) -> AnalyticsEventResponse:
    """Persist one analytics event without touching commerce state."""

    if payload.product_id is not None:
        product = await session.get(Product, payload.product_id)
        if product is None:
            raise ApiError(404, "product_not_found", "The product was not found.")
    event = AnalyticsEvent(
        id=uuid4(),
        event_type=payload.event_type,
        session_id=payload.session_id,
        product_id=payload.product_id,
        source=payload.source or "direct",
        campaign=payload.campaign,
        event_metadata=dict(payload.metadata),
        created_at=datetime.now(UTC),
    )
    session.add(event)
    await session.commit()
    logger.info(
        "analytics_event_recorded",
        extra={"event_type": event.event_type, "source": event.source},
    )
    return AnalyticsEventResponse(
        id=event.id, event_type=event.event_type, created_at=event.created_at
    )


async def product_engagement_counts(
    session: AsyncSession,
    *,
    product_id: UUID,
    period_start: datetime,
) -> dict[str, int]:
    """Count views, shares, and WhatsApp clicks for one product since period_start."""

    rows = (
        await session.execute(
            select(AnalyticsEvent.event_type, func.count(AnalyticsEvent.id))
            .where(
                AnalyticsEvent.product_id == product_id,
                AnalyticsEvent.created_at >= period_start,
            )
            .group_by(AnalyticsEvent.event_type)
        )
    ).all()
    counts = {row[0]: int(row[1]) for row in rows}
    return {
        "views": counts.get(AnalyticsEventType.PRODUCT_VIEW, 0),
        "shares": counts.get(AnalyticsEventType.SHARE_CLICK, 0),
        "whatsapp_clicks": counts.get(AnalyticsEventType.WHATSAPP_CLICK, 0),
    }


async def top_engaged_products(
    session: AsyncSession,
    *,
    period_start: datetime,
    limit: int = 5,
) -> list[ProductEngagement]:
    """Return the most-viewed products with their WhatsApp click counts."""

    view_count = (
        func.count(AnalyticsEvent.id)
        .filter(AnalyticsEvent.event_type == AnalyticsEventType.PRODUCT_VIEW)
        .label("views")
    )
    whatsapp_count = (
        func.count(AnalyticsEvent.id)
        .filter(AnalyticsEvent.event_type == AnalyticsEventType.WHATSAPP_CLICK)
        .label("whatsapp_clicks")
    )
    rows = (
        await session.execute(
            select(
                Product.id,
                Product.name,
                view_count,
                whatsapp_count,
            )
            .join(AnalyticsEvent, AnalyticsEvent.product_id == Product.id)
            .where(AnalyticsEvent.created_at >= period_start)
            .group_by(Product.id, Product.name)
            .order_by(view_count.desc(), Product.name.asc())
            .limit(limit)
        )
    ).all()
    return [
        {
            "product_id": row[0],
            "product_name": row[1],
            "views": int(row[2]),
            "whatsapp_clicks": int(row[3]),
        }
        for row in rows
    ]
