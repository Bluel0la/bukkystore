from __future__ import annotations

from typing import Any, ClassVar

import pytest

from bukkystore_api.commerce.payments import (
    FakePaymentProvider,
    OpayCallback,
    OpayPaymentProvider,
    PaymentInitializationRequest,
    PaymentProviderError,
    build_payment_provider,
)


class ProviderResponse:
    def __init__(self, body: dict[str, Any]) -> None:
        self.body = body

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, Any]:
        return self.body


class ProviderClient:
    responses: ClassVar[list[ProviderResponse]] = []
    requests: ClassVar[list[dict[str, Any]]] = []

    def __init__(self, *, timeout: int) -> None:
        assert timeout == 15

    async def __aenter__(self) -> ProviderClient:
        return self

    async def __aexit__(self, *_args: object) -> None:
        return None

    async def post(self, url: str, **kwargs: Any) -> ProviderResponse:
        self.requests.append({"url": url, **kwargs})
        return self.responses.pop(0)


def opay_provider() -> OpayPaymentProvider:
    return OpayPaymentProvider(
        merchant_id="merchant-123",
        public_key="OPAYPUB-test-key",
        secret_key="OPAYPRV-test-key",
        callback_url="https://api.example.com/api/v1/payments/opay/callback",
        site_url="https://shop.example.com",
    )


def payment_request() -> PaymentInitializationRequest:
    return PaymentInitializationRequest(
        reference="BKS-REFERENCE",
        amount_minor=20_000,
        currency="NGN",
        customer_email="customer@example.com",
        customer_phone="08012345678",
        order_number="BS-20260829-TEST",
        order_access_token="a" * 48,
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
            order_access_token="a" * 48,
        )
    )

    assert response.provider_reference == "fake-BKS-REFERENCE"
    assert str(response.payment_url).startswith("http://localhost:3000/checkout/payment-demo")
    assert "token=" in str(response.payment_url)


def test_unknown_payment_provider_fails_closed() -> None:
    with pytest.raises(ValueError, match="not configured"):
        build_payment_provider("unknown", "http://localhost:3000")


def test_opay_callback_signature_is_verified() -> None:
    provider = opay_provider()
    callback = OpayCallback.model_validate(
        {
            "payload": {
                "amount": "49160",
                "currency": "NGN",
                "reference": "BKS-REFERENCE",
                "refunded": False,
                "status": "SUCCESS",
                "timestamp": "2022-05-07T06:20:46Z",
                "token": "220507145660712931829",
                "transactionId": "220507145660712931829",
            },
            "sha512": "0" * 128,
            "type": "transaction-status",
        }
    )
    content = (
        '{Amount:"49160",Currency:"NGN",Reference:"BKS-REFERENCE",Refunded:f,'
        'Status:"SUCCESS",Timestamp:"2022-05-07T06:20:46Z",'
        'Token:"220507145660712931829",TransactionID:"220507145660712931829"}'
    )
    import hashlib
    import hmac

    callback.sha512 = hmac.new(b"OPAYPRV-test-key", content.encode(), hashlib.sha3_512).hexdigest()

    assert provider.callback_is_authentic(callback) is True
    callback.sha512 = "f" * 128
    assert provider.callback_is_authentic(callback) is False


async def test_opay_initializes_hosted_cashier(monkeypatch: pytest.MonkeyPatch) -> None:
    ProviderClient.responses = [
        ProviderResponse(
            {
                "code": "00000",
                "data": {
                    "reference": "BKS-REFERENCE",
                    "orderNo": "211009140896553163",
                    "cashierUrl": "https://sandboxcashier.opaycheckout.com/pay/token",
                },
            }
        )
    ]
    ProviderClient.requests = []
    monkeypatch.setattr("bukkystore_api.commerce.payments.httpx.AsyncClient", ProviderClient)

    response = await opay_provider().initialize(payment_request())

    assert response.provider_reference == "211009140896553163"
    assert str(response.payment_url) == "https://sandboxcashier.opaycheckout.com/pay/token"
    request = ProviderClient.requests[0]
    assert request["url"].endswith("/cashier/create")
    assert request["headers"]["Authorization"] == "Bearer OPAYPUB-test-key"
    assert request["json"]["amount"] == {"currency": "NGN", "total": 20_000}
    assert "token=" in request["json"]["returnUrl"]


async def test_opay_rejects_invalid_initialization_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ProviderClient.responses = [ProviderResponse({"code": "02000", "message": "failed"})]
    ProviderClient.requests = []
    monkeypatch.setattr("bukkystore_api.commerce.payments.httpx.AsyncClient", ProviderClient)

    with pytest.raises(PaymentProviderError):
        await opay_provider().initialize(payment_request())


@pytest.mark.parametrize(
    ("provider_status", "expected_status"),
    [("SUCCESS", "SUCCESS"), ("FAIL", "FAILED"), ("CLOSE", "FAILED")],
)
async def test_opay_queries_authoritative_terminal_status(
    monkeypatch: pytest.MonkeyPatch, provider_status: str, expected_status: str
) -> None:
    ProviderClient.responses = [
        ProviderResponse(
            {
                "code": "00000",
                "data": {
                    "reference": "BKS-REFERENCE",
                    "orderNo": "211009140896553163",
                    "status": provider_status,
                    "amount": {"total": 20_000, "currency": "NGN"},
                },
            }
        )
    ]
    ProviderClient.requests = []
    monkeypatch.setattr("bukkystore_api.commerce.payments.httpx.AsyncClient", ProviderClient)

    confirmation = await opay_provider().query_confirmation("BKS-REFERENCE")

    assert confirmation is not None
    assert confirmation.status == expected_status
    assert confirmation.provider_reference == "211009140896553163"
    request = ProviderClient.requests[0]
    assert request["url"].endswith("/cashier/status")
    assert request["content"] == '{"country":"NG","reference":"BKS-REFERENCE"}'
    assert request["headers"]["Authorization"].startswith("Bearer ")


async def test_opay_leaves_non_terminal_payment_pending(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ProviderClient.responses = [
        ProviderResponse(
            {
                "code": "00000",
                "data": {
                    "reference": "BKS-REFERENCE",
                    "orderNo": "211009140896553163",
                    "status": "PENDING",
                    "amount": {"total": 20_000, "currency": "NGN"},
                },
            }
        )
    ]
    ProviderClient.requests = []
    monkeypatch.setattr("bukkystore_api.commerce.payments.httpx.AsyncClient", ProviderClient)

    assert await opay_provider().query_confirmation("BKS-REFERENCE") is None


def test_builds_configured_opay_provider_and_rejects_missing_keys() -> None:
    provider = build_payment_provider(
        "opay",
        "https://shop.example.com",
        opay_merchant_id="merchant-123",
        opay_public_key="OPAYPUB-test-key",
        opay_secret_key="OPAYPRV-test-key",
        opay_callback_url="https://api.example.com/api/v1/payments/opay/callback",
    )
    assert isinstance(provider, OpayPaymentProvider)

    with pytest.raises(ValueError, match="not configured"):
        build_payment_provider("opay", "https://shop.example.com")
