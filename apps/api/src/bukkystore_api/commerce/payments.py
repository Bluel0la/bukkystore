from __future__ import annotations

import hashlib
import hmac
import json
from typing import Literal, Protocol
from urllib.parse import urlencode

import httpx
from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field


class PaymentInitializationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reference: str = Field(min_length=8, max_length=64)
    amount_minor: int = Field(ge=0)
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    customer_email: str | None
    customer_phone: str
    order_number: str
    order_access_token: str = Field(min_length=32, max_length=128)


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


class OpayCallbackPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")

    amount: str = Field(min_length=1, max_length=32)
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    reference: str = Field(min_length=8, max_length=64)
    refunded: bool
    status: str = Field(min_length=1, max_length=30)
    timestamp: str = Field(min_length=1, max_length=64)
    token: str | None = Field(default=None, max_length=160)
    transactionId: str = Field(min_length=1, max_length=160)


class OpayCallback(BaseModel):
    model_config = ConfigDict(extra="ignore")

    payload: OpayCallbackPayload
    sha512: str = Field(pattern=r"^[A-Fa-f0-9]{128}$")
    type: Literal["transaction-status"]


class FakePaymentProvider:
    name = "fake"

    def __init__(self, site_url: str) -> None:
        self.site_url = site_url.rstrip("/")

    async def initialize(
        self, request: PaymentInitializationRequest
    ) -> PaymentInitializationResponse:
        query = {
            "reference": request.reference,
            "order": request.order_number,
            "token": request.order_access_token,
        }
        return PaymentInitializationResponse(
            provider_reference=f"fake-{request.reference}",
            payment_url=AnyHttpUrl(f"{self.site_url}/checkout/payment-demo?{urlencode(query)}"),
        )


class OpayPaymentProvider:
    name = "opay"

    def __init__(
        self,
        *,
        merchant_id: str,
        public_key: str,
        secret_key: str,
        callback_url: str,
        site_url: str,
        environment: Literal["sandbox", "production"] = "sandbox",
    ) -> None:
        self.merchant_id = merchant_id
        self.public_key = public_key
        self.secret_key = secret_key
        self.callback_url = callback_url
        self.site_url = site_url.rstrip("/")
        host = (
            "testapi.opaycheckout.com" if environment == "sandbox" else "liveapi.opaycheckout.com"
        )
        self.base_url = f"https://{host}/api/v1/international"

    async def initialize(
        self, request: PaymentInitializationRequest
    ) -> PaymentInitializationResponse:
        status_url = (
            f"{self.site_url}/orders/{request.order_number}?"
            f"{urlencode({'token': request.order_access_token})}"
        )
        payload: dict[str, object] = {
            "amount": {"currency": request.currency, "total": request.amount_minor},
            "callbackUrl": self.callback_url,
            "cancelUrl": status_url,
            "country": "NG",
            "customerVisitSource": "BROWSER",
            "expireAt": 15,
            "product": {
                "description": f"Order {request.order_number}",
                "name": "Atiten Kids Store order",
            },
            "reference": request.reference,
            "returnUrl": status_url,
            "userInfo": {
                "userEmail": request.customer_email or "",
                "userId": request.order_number,
                "userMobile": request.customer_phone,
            },
        }
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.post(
                    f"{self.base_url}/cashier/create",
                    headers={
                        "Accept": "application/json",
                        "Authorization": f"Bearer {self.public_key}",
                        "MerchantId": self.merchant_id,
                    },
                    json=payload,
                )
            response.raise_for_status()
            body = response.json()
            data = body.get("data") if isinstance(body, dict) else None
            if body.get("code") != "00000" or not isinstance(data, dict):
                raise PaymentProviderError
            if data.get("reference") != request.reference:
                raise PaymentProviderError
            return PaymentInitializationResponse(
                provider_reference=str(data["orderNo"]),
                payment_url=AnyHttpUrl(str(data["cashierUrl"])),
            )
        except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
            raise PaymentProviderError from exc

    def callback_is_authentic(self, callback: OpayCallback) -> bool:
        payload = callback.payload
        content = (
            f'{{Amount:"{payload.amount}",Currency:"{payload.currency}",'
            f'Reference:"{payload.reference}",Refunded:{"t" if payload.refunded else "f"},'
            f'Status:"{payload.status}",Timestamp:"{payload.timestamp}",'
            f'Token:"{payload.token or ""}",TransactionID:"{payload.transactionId}"}}'
        )
        expected = hmac.new(
            self.secret_key.encode(), content.encode(), hashlib.sha3_512
        ).hexdigest()
        return hmac.compare_digest(expected.lower(), callback.sha512.lower())

    async def query_confirmation(self, reference: str) -> PaymentConfirmation | None:
        payload = {"country": "NG", "reference": reference}
        serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        signature = hmac.new(
            self.secret_key.encode(), serialized.encode(), hashlib.sha512
        ).hexdigest()
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.post(
                    f"{self.base_url}/cashier/status",
                    content=serialized,
                    headers={
                        "Accept": "application/json",
                        "Authorization": f"Bearer {signature}",
                        "Content-Type": "application/json",
                        "MerchantId": self.merchant_id,
                    },
                )
            response.raise_for_status()
            body = response.json()
            data = body.get("data") if isinstance(body, dict) else None
            if body.get("code") != "00000" or not isinstance(data, dict):
                raise PaymentProviderError
            if data.get("reference") != reference:
                raise PaymentProviderError
            status = str(data.get("status", "")).upper()
            if status in {"INITIAL", "PENDING"}:
                return None
            if status not in {"SUCCESS", "FAIL", "CLOSE"}:
                raise PaymentProviderError
            normalized_status: Literal["SUCCESS", "FAILED"] = (
                "SUCCESS" if status == "SUCCESS" else "FAILED"
            )
            amount = data.get("amount")
            if not isinstance(amount, dict):
                raise PaymentProviderError
            order_number = str(data["orderNo"])
            return PaymentConfirmation(
                provider=self.name,
                event_key=f"status:{order_number}:{status}",
                internal_reference=reference,
                provider_reference=order_number,
                amount_minor=int(amount["total"]),
                currency=str(amount["currency"]),
                status=normalized_status,
            )
        except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
            raise PaymentProviderError from exc


def build_payment_provider(
    provider: str,
    site_url: str,
    *,
    opay_environment: Literal["sandbox", "production"] = "sandbox",
    opay_merchant_id: str | None = None,
    opay_public_key: str | None = None,
    opay_secret_key: str | None = None,
    opay_callback_url: str | None = None,
) -> PaymentProvider:
    if provider == "fake":
        return FakePaymentProvider(site_url)
    if provider == "opay":
        if not all((opay_merchant_id, opay_public_key, opay_secret_key, opay_callback_url)):
            raise ValueError("The selected payment provider is not configured")
        assert opay_merchant_id is not None
        assert opay_public_key is not None
        assert opay_secret_key is not None
        assert opay_callback_url is not None
        return OpayPaymentProvider(
            merchant_id=opay_merchant_id,
            public_key=opay_public_key,
            secret_key=opay_secret_key,
            callback_url=opay_callback_url,
            site_url=site_url,
            environment=opay_environment,
        )
    raise ValueError("The selected payment provider is not configured")
