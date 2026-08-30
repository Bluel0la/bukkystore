from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AnalyticsRangeQuery(BaseModel):
    """Bound the reporting window to protect aggregate queries."""

    model_config = ConfigDict(extra="forbid")

    days: int = Field(default=30, ge=1, le=365)


class TopProductMetric(BaseModel):
    product_id: UUID
    product_name: str
    units_sold: int
    sales_minor: int


class SourceMetric(BaseModel):
    source: str
    orders: int
    sales_minor: int


class LowStockMetric(BaseModel):
    variant_id: UUID
    product_id: UUID
    product_name: str
    variant_name: str
    sku: str
    available_quantity: int
    low_stock_threshold: int


class AdminAnalyticsOverview(BaseModel):
    generated_at: datetime
    period_start: datetime
    range_days: int
    currency: Literal["NGN"] = "NGN"
    total_orders: int
    sales_orders: int
    sales_minor: int
    average_order_minor: int
    awaiting_payment_orders: int
    open_fulfilment_orders: int
    pending_refunds: int
    low_stock_variants: int
    top_products: list[TopProductMetric]
    sources: list[SourceMetric]
    low_stock: list[LowStockMetric]
