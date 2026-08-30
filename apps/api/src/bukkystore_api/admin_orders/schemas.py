from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from bukkystore_api.commerce.models import OrderStatus, PaymentStatus


class AdminOrderSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AdminOrderListQuery(AdminOrderSchema):
    status: OrderStatus | None = None
    search: (
        Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=120)]
        | None
    ) = None
    limit: int = Field(default=50, ge=1, le=100)


class AdminOrderItem(AdminOrderSchema):
    id: UUID
    product_name: str
    variant_name: str
    sku: str
    unit_price_minor: int
    quantity: int
    line_subtotal_minor: int


class AdminOrderSummary(AdminOrderSchema):
    id: UUID
    order_number: str
    customer_full_name: str
    customer_phone: str
    total_minor: int
    currency: str
    status: OrderStatus
    payment_status: PaymentStatus
    created_at: datetime


class AdminOrderDetail(AdminOrderSummary):
    customer_email: str | None
    delivery_area_name: str
    delivery_address: str
    delivery_directions: str | None
    subtotal_minor: int
    delivery_fee_minor: int
    items: list[AdminOrderItem]


class AdminOrderPage(AdminOrderSchema):
    items: list[AdminOrderSummary]
