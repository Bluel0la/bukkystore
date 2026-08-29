from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession

from bukkystore_api.commerce.schemas import (
    CheckoutRequest,
    CheckoutResponse,
    DeliveryAreaResponse,
)
from bukkystore_api.commerce.service import create_checkout, list_delivery_areas
from bukkystore_api.dependencies import get_session
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
