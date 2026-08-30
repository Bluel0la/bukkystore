from __future__ import annotations

from datetime import datetime
from typing import Annotated, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from bukkystore_api.commerce.models import OrderStatus, PaymentStatus

Name = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=2,
        max_length=120,
        pattern=r"^\S.*\S$",
    ),
]
Phone = Annotated[
    str,
    StringConstraints(strip_whitespace=True, pattern=r"^(?:\+234|0)[789]\d{9}$"),
]
Email = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        to_lower=True,
        min_length=5,
        max_length=254,
        pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$",
    ),
]
BoundedText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=3, pattern=r"^\S.{1,}\S$"),
]


class CommerceSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DeliveryAreaResponse(CommerceSchema):
    id: UUID
    name: str
    fee_minor: int
    currency: str


class CheckoutCustomer(CommerceSchema):
    full_name: Name
    phone: Phone
    email: Email | None = None


class CheckoutDelivery(CommerceSchema):
    area_id: UUID
    address: Annotated[BoundedText, StringConstraints(max_length=500)]
    directions: (
        Annotated[
            str,
            StringConstraints(
                strip_whitespace=True,
                min_length=3,
                max_length=500,
                pattern=r"^\S.{1,}\S$",
            ),
        ]
        | None
    ) = None


class CheckoutItem(CommerceSchema):
    variant_id: UUID
    quantity: int = Field(ge=1, le=20)


class CheckoutAttribution(CommerceSchema):
    source: Annotated[
        str,
        StringConstraints(
            strip_whitespace=True,
            min_length=1,
            max_length=50,
            pattern=r"^\S(?:.*\S)?$",
        ),
    ]
    campaign: (
        Annotated[
            str,
            StringConstraints(
                strip_whitespace=True,
                min_length=1,
                max_length=100,
                pattern=r"^\S(?:.*\S)?$",
            ),
        ]
        | None
    ) = None


class CheckoutRequest(CommerceSchema):
    customer: CheckoutCustomer
    delivery: CheckoutDelivery
    items: list[CheckoutItem] = Field(min_length=1, max_length=50)
    attribution: CheckoutAttribution | None = None

    @model_validator(mode="after")
    def reject_duplicate_variants(self) -> Self:
        ids = [item.variant_id for item in self.items]
        if len(ids) != len(set(ids)):
            raise ValueError("Each variant may appear only once")
        return self


class CheckoutSummary(CommerceSchema):
    subtotal_minor: int
    delivery_fee_minor: int
    total_minor: int
    currency: str


class CheckoutResponse(CommerceSchema):
    order_number: str
    order_status: OrderStatus
    payment_status: PaymentStatus
    reservation_expires_at: datetime
    summary: CheckoutSummary
    payment_url: str
    order_access_token: str
    idempotent_replay: bool


class FakePaymentConfirmationRequest(CommerceSchema):
    order_number: Annotated[
        str,
        StringConstraints(
            strip_whitespace=True,
            min_length=12,
            max_length=32,
            pattern=r"^\S.{10,}\S$",
        ),
    ]
    order_access_token: Annotated[str, StringConstraints(min_length=32, max_length=128)]


class PaymentStatusResponse(CommerceSchema):
    order_number: str
    order_status: OrderStatus
    payment_status: PaymentStatus
    reservation_expires_at: datetime
    paid_at: datetime | None = None
    summary: CheckoutSummary
