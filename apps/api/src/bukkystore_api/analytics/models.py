from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, CheckConstraint, DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from bukkystore_api.database import Base


class AnalyticsEventType:
    """Allowlisted browsing/conversion events accepted by the ingestion endpoint."""

    PRODUCT_VIEW = "product_view"
    SHARE_CLICK = "share_click"
    WHATSAPP_CLICK = "whatsapp_click"

    ALL = (PRODUCT_VIEW, SHARE_CLICK, WHATSAPP_CLICK)


class AnalyticsEvent(Base):
    """Append-only browsing/conversion event kept separate from commerce state.

    Analytics must never block or roll back purchasing, so this table is
    written by its own endpoint and read only by aggregate reporting queries.
    """

    __tablename__ = "analytics_events"
    __table_args__ = (
        CheckConstraint(
            "event_type IN ('product_view', 'share_click', 'whatsapp_click')",
            name="event_type_allowlist",
        ),
        Index("ix_analytics_events_product_created", "product_id", "created_at"),
        Index("ix_analytics_events_type_created", "event_type", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type: Mapped[str] = mapped_column(String(30), nullable=False)
    session_id: Mapped[str] = mapped_column(String(64), nullable=False)
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="SET NULL"), nullable=True
    )
    source: Mapped[str] = mapped_column(String(50), nullable=False, default="direct")
    campaign: Mapped[str | None] = mapped_column(String(100), nullable=True)
    event_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
