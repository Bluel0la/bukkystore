from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from bukkystore_api.admin_orders.schemas import (
    AdminOrderDetail,
    AdminOrderListQuery,
    AdminOrderPage,
    OrderCancellationRequest,
    OrderTransitionRequest,
    RefundCompletionRequest,
)
from bukkystore_api.admin_orders.service import (
    cancel_order,
    complete_refund,
    get_admin_order,
    list_admin_orders,
    transition_order,
)
from bukkystore_api.auth.dependencies import AdminContext, require_admin, require_csrf
from bukkystore_api.dependencies import get_session
from bukkystore_api.schemas import ErrorResponse

router = APIRouter(
    prefix="/api/v1/admin",
    tags=["Admin orders"],
    responses={401: {"model": ErrorResponse, "description": "Administrator sign-in is required."}},
)
Session = Annotated[AsyncSession, Depends(get_session)]
Authenticated = Annotated[AdminContext, Depends(require_admin)]
MutatingAdmin = Annotated[AdminContext, Depends(require_csrf)]
IdempotencyKey = Annotated[
    str,
    Header(
        alias="Idempotency-Key",
        min_length=16,
        max_length=120,
        pattern=r"^[A-Za-z0-9:_-]+$",
    ),
]


@router.get("/orders", response_model=AdminOrderPage, summary="List store orders")
async def orders(
    session: Session,
    _admin: Authenticated,
    filters: Annotated[AdminOrderListQuery, Query()],
) -> AdminOrderPage:
    """List recent orders with server-side status and search filters."""

    return await list_admin_orders(session, filters)


@router.get(
    "/orders/{order_id}",
    response_model=AdminOrderDetail,
    responses={404: {"model": ErrorResponse}},
    summary="Get an order for fulfilment",
)
async def order_detail(order_id: UUID, session: Session, _admin: Authenticated) -> AdminOrderDetail:
    """Return customer, delivery, item, and payment detail for one order."""

    return await get_admin_order(session, order_id)


@router.post(
    "/orders/{order_id}/transitions",
    response_model=AdminOrderDetail,
    responses={409: {"model": ErrorResponse}},
    summary="Advance a paid order through fulfilment",
)
async def order_transition(
    order_id: UUID,
    payload: OrderTransitionRequest,
    session: Session,
    admin: MutatingAdmin,
    request: Request,
    idempotency_key: IdempotencyKey,
) -> AdminOrderDetail:
    """Apply one explicit, one-way fulfilment action to a paid order."""

    return await transition_order(
        session,
        order_id,
        payload,
        actor_user_id=admin.user.id,
        idempotency_key=idempotency_key,
        secret=request.app.state.settings.session_secret.get_secret_value(),
    )


@router.post(
    "/orders/{order_id}/cancellations",
    response_model=AdminOrderDetail,
    responses={409: {"model": ErrorResponse}},
    summary="Cancel an order safely",
)
async def order_cancellation(
    order_id: UUID,
    payload: OrderCancellationRequest,
    session: Session,
    admin: MutatingAdmin,
    request: Request,
    idempotency_key: IdempotencyKey,
) -> AdminOrderDetail:
    """Release or restore inventory once and create a refund obligation when paid."""

    return await cancel_order(
        session,
        order_id,
        payload,
        actor_user_id=admin.user.id,
        idempotency_key=idempotency_key,
        secret=request.app.state.settings.session_secret.get_secret_value(),
    )


@router.post(
    "/refunds/{refund_id}/complete",
    response_model=AdminOrderDetail,
    responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
    summary="Record a completed manual refund",
)
async def refund_complete(
    refund_id: UUID,
    payload: RefundCompletionRequest,
    session: Session,
    admin: MutatingAdmin,
    request: Request,
    idempotency_key: IdempotencyKey,
) -> AdminOrderDetail:
    """Mark a pending manual refund sent without repeating payment effects."""

    return await complete_refund(
        session,
        refund_id,
        payload,
        actor_user_id=admin.user.id,
        idempotency_key=idempotency_key,
        secret=request.app.state.settings.session_secret.get_secret_value(),
    )
