from __future__ import annotations

from typing import Literal, Protocol
from urllib.parse import urlencode

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field


class PaymentInitializationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reference: str = Field(min_length=8, max_length=64)
    amount_minor: int = Field(ge=0)
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    customer_email: str | None
    customer_phone: str
    order_number: str


class PaymentInitializationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider_reference: str = Field(min_length=1, max_length=128)
    payment_url: AnyHttpUrl


class PaymentConfirmation(BaseModel):
    """Normalized, already-authenticated result from a payment provider boundary."""

    model_config = ConfigDict(extra="forbid")

    provider: str = Field(min_length=1, max_length=30)
    event_key: str = Field(min_length=1, max_length=160)
    internal_reference: str = Field(min_length=8, max_length=64)
    provider_reference: str = Field(min_length=1, max_length=128)
    amount_minor: int = Field(ge=0)
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    status: Literal["SUCCESS", "FAILED"]


class PaymentProviderError(Exception):
    """Safe provider-boundary failure without upstream response details."""


class PaymentProvider(Protocol):
    name: str

    async def initialize(
        self, request: PaymentInitializationRequest
    ) -> PaymentInitializationResponse: ...


class FakePaymentProvider:
    name = "fake"

    def __init__(self, site_url: str) -> None:
        self.site_url = site_url.rstrip("/")

    async def initialize(
        self, request: PaymentInitializationRequest
    ) -> PaymentInitializationResponse:
        return PaymentInitializationResponse(
            provider_reference=f"fake-{request.reference}",
            payment_url=(
                f"{self.site_url}/checkout/payment-demo?"
                f"{urlencode({'reference': request.reference, 'order': request.order_number})}"
            ),
        )


def build_payment_provider(provider: str, site_url: str) -> PaymentProvider:
    if provider == "fake":
        return FakePaymentProvider(site_url)
    raise ValueError("The selected payment provider is not configured")
