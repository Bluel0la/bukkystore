from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from bukkystore_api.commerce.payments import (
    OpayCallback,
    OpayPaymentProvider,
    PaymentProviderError,
)
from bukkystore_api.commerce.schemas import (
    CheckoutRequest,
    CheckoutResponse,
    DeliveryAreaResponse,
    FakePaymentConfirmationRequest,
    PaymentStatusResponse,
)
from bukkystore_api.commerce.service import (
    confirm_fake_payment,
    confirm_payment,
    create_checkout,
    get_payment_status,
    list_delivery_areas,
)
from bukkystore_api.dependencies import get_session
from bukkystore_api.errors import ApiError
from bukkystore_api.schemas import ErrorResponse

router = APIRouter(prefix="/api/v1", tags=["Commerce"])
Session = Annotated[AsyncSession, Depends(get_session)]
IdempotencyKey = Annotated[
    str,
    Header(
        alias="Idempotency-Key",
        min_length=16,
        max_length=120,
        pattern=r"^[A-Za-z0-9:_-]+$",
    ),
]


@router.get(
    "/delivery-areas",
    response_model=list[DeliveryAreaResponse],
    summary="List active Lagos delivery areas",
)
async def delivery_areas(session: Session) -> list[DeliveryAreaResponse]:
    """Return the simple named delivery areas and server-owned fees available at checkout."""

    return await list_delivery_areas(session)


@router.post(
    "/checkout",
    response_model=CheckoutResponse,
    status_code=201,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
    summary="Create a guest order and reserve its stock",
)
async def checkout(
    payload: CheckoutRequest,
    session: Session,
    request: Request,
    idempotency_key: IdempotencyKey,
) -> CheckoutResponse:
    """Calculate authoritative totals, reserve variants, and initialize hosted payment."""

    settings = request.app.state.settings
    return await create_checkout(
        session,
        payload,
        idempotency_key=idempotency_key,
        secret=settings.session_secret.get_secret_value(),
        reservation_minutes=settings.reservation_minutes,
        provider=request.app.state.payment_provider,
    )


@router.get(
    "/orders/{order_number}/payment-status",
    response_model=PaymentStatusResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Check a guest order's payment status",
)
async def payment_status(
    order_number: str,
    session: Session,
    request: Request,
    token: Annotated[str, Query(min_length=32, max_length=128)],
) -> PaymentStatusResponse:
    """Return a payment-safe order summary when its high-entropy guest token matches."""

    return await get_payment_status(
        session,
        order_number=order_number,
        access_token=token,
        secret=request.app.state.settings.session_secret.get_secret_value(),
    )


@router.post(
    "/payments/fake/confirm",
    response_model=PaymentStatusResponse,
    responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
    summary="Confirm a development-only fake payment",
)
async def fake_payment_confirmation(
    payload: FakePaymentConfirmationRequest, session: Session, request: Request
) -> PaymentStatusResponse:
    """Exercise the real confirmation transaction without exposing provider-owned fields."""

    settings = request.app.state.settings
    if settings.environment == "production" or settings.payment_provider != "fake":
        raise ApiError(404, "not_found", "The requested resource was not found.")
    return await confirm_fake_payment(
        session,
        order_number=payload.order_number,
        access_token=payload.order_access_token,
        secret=settings.session_secret.get_secret_value(),
    )


@router.post(
    "/payments/opay/callback",
    status_code=200,
    response_class=Response,
    responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    summary="Receive and verify an OPay payment notification",
)
async def opay_payment_callback(
    payload: OpayCallback, session: Session, request: Request
) -> Response:
    """Authenticate the callback, cross-check OPay, then apply the payment exactly once."""

    provider = request.app.state.payment_provider
    if not isinstance(provider, OpayPaymentProvider):
        raise ApiError(404, "not_found", "The requested resource was not found.")
    if not provider.callback_is_authentic(payload):
        raise ApiError(401, "invalid_payment_signature", "The payment notification is invalid.")
    try:
        confirmation = await provider.query_confirmation(payload.payload.reference)
    except PaymentProviderError as exc:
        raise ApiError(
            503,
            "payment_verification_unavailable",
            "The payment notification could not be verified.",
        ) from exc
    if confirmation is not None:
        await confirm_payment(session, confirmation)
    return Response(status_code=200)
