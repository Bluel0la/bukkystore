from __future__ import annotations

import pytest

from bukkystore_api.commerce.payments import (
    FakePaymentProvider,
    PaymentInitializationRequest,
    build_payment_provider,
)


async def test_fake_payment_provider_returns_deterministic_handoff() -> None:
    provider = FakePaymentProvider("http://localhost:3000/")

    response = await provider.initialize(
        PaymentInitializationRequest(
            reference="BKS-REFERENCE",
            amount_minor=2_000_00,
            currency="NGN",
            customer_email=None,
            customer_phone="08012345678",
            order_number="BS-20260829-TEST",
        )
    )

    assert response.provider_reference == "fake-BKS-REFERENCE"
    assert str(response.payment_url).startswith("http://localhost:3000/checkout/payment-demo")


def test_unknown_payment_provider_fails_closed() -> None:
    with pytest.raises(ValueError, match="not configured"):
        build_payment_provider("unknown", "http://localhost:3000")
