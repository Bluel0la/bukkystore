from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from bukkystore_api.admin_orders.schemas import (
    AdminOrderDetail,
    AdminOrderListQuery,
    AdminOrderPage,
)
from bukkystore_api.admin_orders.service import get_admin_order, list_admin_orders
from bukkystore_api.auth.dependencies import AdminContext, require_admin
from bukkystore_api.dependencies import get_session
from bukkystore_api.schemas import ErrorResponse

router = APIRouter(
    prefix="/api/v1/admin/orders",
    tags=["Admin orders"],
    responses={401: {"model": ErrorResponse, "description": "Administrator sign-in is required."}},
)
Session = Annotated[AsyncSession, Depends(get_session)]
Authenticated = Annotated[AdminContext, Depends(require_admin)]


@router.get("", response_model=AdminOrderPage, summary="List store orders")
async def orders(
    session: Session,
    _admin: Authenticated,
    filters: Annotated[AdminOrderListQuery, Query()],
) -> AdminOrderPage:
    """List recent orders with server-side status and search filters."""

    return await list_admin_orders(session, filters)


@router.get(
    "/{order_id}",
    response_model=AdminOrderDetail,
    responses={404: {"model": ErrorResponse}},
    summary="Get an order for fulfilment",
)
async def order_detail(order_id: UUID, session: Session, _admin: Authenticated) -> AdminOrderDetail:
    """Return customer, delivery, item, and payment detail for one order."""

    return await get_admin_order(session, order_id)
