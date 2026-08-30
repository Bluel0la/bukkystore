from __future__ import annotations

from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from bukkystore_api.admin_orders.schemas import (
    AdminOrderDetail,
    AdminOrderItem,
    AdminOrderListQuery,
    AdminOrderPage,
    AdminOrderSummary,
)
from bukkystore_api.commerce.models import Order, PaymentStatus
from bukkystore_api.errors import ApiError


def _latest_payment_status(order: Order) -> PaymentStatus:
    return order.payments[-1].status if order.payments else PaymentStatus.FAILED


def _summary(order: Order) -> AdminOrderSummary:
    return AdminOrderSummary(
        id=order.id,
        order_number=order.order_number,
        customer_full_name=order.customer_full_name,
        customer_phone=order.customer_phone,
        total_minor=order.total_minor,
        currency=order.currency,
        status=order.status,
        payment_status=_latest_payment_status(order),
        created_at=order.created_at,
    )


async def list_admin_orders(session: AsyncSession, filters: AdminOrderListQuery) -> AdminOrderPage:
    statement = (
        select(Order)
        .options(selectinload(Order.payments))
        .order_by(Order.created_at.desc(), Order.id.desc())
        .limit(filters.limit)
    )
    if filters.status is not None:
        statement = statement.where(Order.status == filters.status)
    if filters.search:
        pattern = f"%{filters.search}%"
        statement = statement.where(
            or_(
                Order.order_number.ilike(pattern),
                Order.customer_full_name.ilike(pattern),
                Order.customer_phone.ilike(pattern),
            )
        )
    orders = (await session.scalars(statement)).unique().all()
    return AdminOrderPage(items=[_summary(order) for order in orders])


async def get_admin_order(session: AsyncSession, order_id: UUID) -> AdminOrderDetail:
    order = (
        (
            await session.scalars(
                select(Order)
                .where(Order.id == order_id)
                .options(selectinload(Order.payments), selectinload(Order.items))
            )
        )
        .unique()
        .one_or_none()
    )
    if order is None:
        raise ApiError(404, "order_not_found", "The order could not be found.")
    summary = _summary(order)
    return AdminOrderDetail(
        **summary.model_dump(),
        customer_email=order.customer_email,
        delivery_area_name=order.delivery_area_name,
        delivery_address=order.delivery_address,
        delivery_directions=order.delivery_directions,
        subtotal_minor=order.subtotal_minor,
        delivery_fee_minor=order.delivery_fee_minor,
        items=[
            AdminOrderItem(
                id=item.id,
                product_name=item.product_name,
                variant_name=item.variant_name,
                sku=item.sku,
                unit_price_minor=item.unit_price_minor,
                quantity=item.quantity,
                line_subtotal_minor=item.line_subtotal_minor,
            )
            for item in order.items
        ],
    )
