from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, BigInteger, CheckConstraint, DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from bukkystore_api.database import Base


class StoreSetting(Base):
    """Singleton row holding business-owned store configuration.

    Business settings live in the database, never in source code, so the
    store owner can change identity, contact, social, hours, and minimum-order
    details without a redeploy. Exactly one row may exist.
    """

    __tablename__ = "store_settings"
    __table_args__ = (
        CheckConstraint("singleton_guard = 1", name="singleton_row"),
        CheckConstraint("length(store_name) BETWEEN 2 AND 120", name="store_name_length"),
        CheckConstraint("length(currency) = 3", name="currency_length"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    singleton_guard: Mapped[int] = mapped_column(Integer, nullable=False, default=1, unique=True)
    store_name: Mapped[str] = mapped_column(String(120), nullable=False)
    logo_ref: Mapped[str | None] = mapped_column(String(500), nullable=True)
    whatsapp_number: Mapped[str] = mapped_column(String(20), nullable=False)
    phone_number: Mapped[str] = mapped_column(String(20), nullable=False)
    instagram_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    tiktok_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    address: Mapped[str] = mapped_column(Text, nullable=False)
    city: Mapped[str] = mapped_column(String(120), nullable=False, default="Lagos")
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="NGN")
    minimum_order_minor: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    business_hours: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    last_idempotency_key_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_request_fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
