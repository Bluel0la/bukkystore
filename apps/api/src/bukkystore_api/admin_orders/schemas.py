from __future__ import annotations

import enum
from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from bukkystore_api.commerce.models import OrderStatus, PaymentStatus, RefundStatus


class AdminOrderSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class OrderTransitionAction(enum.StrEnum):
    START_PROCESSING = "START_PROCESSING"
    MARK_OUT_FOR_DELIVERY = "MARK_OUT_FOR_DELIVERY"
    MARK_COMPLETED = "MARK_COMPLETED"


class OrderTransitionRequest(AdminOrderSchema):
    action: OrderTransitionAction


class OrderCancellationRequest(AdminOrderSchema):
    reason: Annotated[str, StringConstraints(strip_whitespace=True, min_length=5, max_length=500)]


class RefundCompletionRequest(AdminOrderSchema):
    manual_reference: (
        Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=120)]
        | None
    ) = None


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


class AdminRefundResponse(AdminOrderSchema):
    id: UUID
    payment_id: UUID
    amount_minor: int
    currency: str
    reason: str
    status: RefundStatus
    manual_reference: str | None
    created_at: datetime
    completed_at: datetime | None


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
    refunds: list[AdminRefundResponse]
    available_actions: list[str]


class AdminOrderPage(AdminOrderSchema):
    items: list[AdminOrderSummary]
