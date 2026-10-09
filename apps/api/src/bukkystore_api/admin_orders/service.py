from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from bukkystore_api.admin_orders.schemas import (
    AdminOrderDetail,
    AdminOrderItem,
    AdminOrderListQuery,
    AdminOrderPage,
    AdminOrderSummary,
    AdminRefundResponse,
    OrderCancellationRequest,
    OrderTransitionAction,
    OrderTransitionRequest,
    RefundCompletionRequest,
)
from bukkystore_api.auth.security import hash_token
from bukkystore_api.catalogue.models import (
    InventoryMovement,
    InventoryMovementType,
    ProductVariant,
)
from bukkystore_api.commerce.models import (
    InventoryReservation,
    Order,
    OrderStatus,
    OrderStatusEvent,
    Payment,
    PaymentStatus,
    Refund,
    RefundMode,
    RefundStatus,
    ReservationStatus,
)
from bukkystore_api.errors import ApiError

logger = logging.getLogger(__name__)


async def _commit_operation(session: AsyncSession) -> None:
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise ApiError(409, "order_operation_conflict", "The order changed concurrently.") from exc


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


def _available_actions(order: Order) -> list[str]:
    actions: dict[OrderStatus, list[str]] = {
        OrderStatus.AWAITING_PAYMENT: ["CANCEL"],
        OrderStatus.CONFIRMED: [OrderTransitionAction.START_PROCESSING.value, "CANCEL"],
        OrderStatus.PROCESSING: [OrderTransitionAction.MARK_OUT_FOR_DELIVERY.value, "CANCEL"],
        OrderStatus.OUT_FOR_DELIVERY: [OrderTransitionAction.MARK_COMPLETED.value],
        OrderStatus.REFUND_REQUIRED: ["CANCEL"],
    }
    result = list(actions.get(order.status, []))
    if any(refund.status is RefundStatus.PENDING for refund in order.refunds):
        result.append("COMPLETE_REFUND")
    return result


def _detail(order: Order) -> AdminOrderDetail:
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
        refunds=[
            AdminRefundResponse(
                id=refund.id,
                payment_id=refund.payment_id,
                amount_minor=refund.amount_minor,
                currency=refund.currency,
                reason=refund.reason,
                status=refund.status,
                manual_reference=refund.manual_reference,
                created_at=refund.created_at,
                completed_at=refund.completed_at,
            )
            for refund in order.refunds
        ],
        available_actions=_available_actions(order),
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
                .options(
                    selectinload(Order.payments),
                    selectinload(Order.items),
                    selectinload(Order.refunds),
                )
            )
        )
        .unique()
        .one_or_none()
    )
    if order is None:
        raise ApiError(404, "order_not_found", "The order could not be found.")
    return _detail(order)


async def _locked_order(session: AsyncSession, order_id: UUID) -> Order:
    # NOTE: no joinedload here — PostgreSQL rejects bare FOR UPDATE over the
    # outer join it produces. selectinload keeps the lock on orders only.
    order = (
        (
            await session.scalars(
                select(Order)
                .where(Order.id == order_id)
                .with_for_update()
                .options(
                    selectinload(Order.items),
                    selectinload(Order.payments),
                    selectinload(Order.refunds),
                    selectinload(Order.reservation).selectinload(InventoryReservation.items),
                )
            )
        )
        .unique()
        .one_or_none()
    )
    if order is None:
        raise ApiError(404, "order_not_found", "The order could not be found.")
    return order


async def _operation_replay(
    session: AsyncSession,
    *,
    key_hash: str,
    order_id: UUID,
    event_type: str,
    reason: str | None = None,
) -> bool:
    event = await session.scalar(
        select(OrderStatusEvent).where(OrderStatusEvent.idempotency_key_hash == key_hash)
    )
    if event is None:
        return False
    if event.order_id != order_id or event.event_type != event_type or event.reason != reason:
        raise ApiError(409, "idempotency_conflict", "The idempotency key was already used.")
    return True


def _latest_payment(order: Order) -> Payment:
    if not order.payments:
        raise ApiError(409, "payment_missing", "The order has no payment to reconcile.")
    return order.payments[-1]


async def transition_order(
    session: AsyncSession,
    order_id: UUID,
    payload: OrderTransitionRequest,
    *,
    actor_user_id: UUID,
    idempotency_key: str,
    secret: str,
) -> AdminOrderDetail:
    order = await _locked_order(session, order_id)
    key_hash = hash_token(idempotency_key, secret)
    if await _operation_replay(
        session,
        key_hash=key_hash,
        order_id=order_id,
        event_type=payload.action.value,
    ):
        return _detail(order)

    transitions = {
        OrderTransitionAction.START_PROCESSING: (
            OrderStatus.CONFIRMED,
            OrderStatus.PROCESSING,
        ),
        OrderTransitionAction.MARK_OUT_FOR_DELIVERY: (
            OrderStatus.PROCESSING,
            OrderStatus.OUT_FOR_DELIVERY,
        ),
        OrderTransitionAction.MARK_COMPLETED: (
            OrderStatus.OUT_FOR_DELIVERY,
            OrderStatus.COMPLETED,
        ),
    }
    expected, target = transitions[payload.action]
    if order.status is not expected:
        raise ApiError(409, "invalid_order_transition", "That order action is not available.")
    if _latest_payment(order).status is not PaymentStatus.SUCCESS:
        raise ApiError(409, "payment_not_successful", "Only a paid order can be fulfilled.")

    previous = order.status
    order.status = target
    session.add(
        OrderStatusEvent(
            order=order,
            previous_status=previous,
            new_status=target,
            event_type=payload.action.value,
            idempotency_key_hash=key_hash,
            actor_user_id=actor_user_id,
        )
    )
    await _commit_operation(session)
    logger.info(
        "order_status_changed",
        extra={
            "order_id": str(order.id),
            "previous_status": previous.value,
            "status": target.value,
            "changed_at": datetime.now(UTC).isoformat(),
            "trigger": payload.action.value,
        },
    )
    return _detail(order)


async def _locked_variants(
    session: AsyncSession, variant_ids: list[UUID]
) -> dict[UUID, ProductVariant]:
    unique_ids = sorted(set(variant_ids))
    variants = list(
        (
            await session.scalars(
                select(ProductVariant)
                .where(ProductVariant.id.in_(unique_ids))
                .order_by(ProductVariant.id)
                .with_for_update()
            )
        ).all()
    )
    if len(variants) != len(unique_ids):
        raise ApiError(409, "inventory_inconsistent", "The order cannot be reconciled.")
    return {variant.id: variant for variant in variants}


async def cancel_order(
    session: AsyncSession,
    order_id: UUID,
    payload: OrderCancellationRequest,
    *,
    actor_user_id: UUID,
    idempotency_key: str,
    secret: str,
) -> AdminOrderDetail:
    order = await _locked_order(session, order_id)
    key_hash = hash_token(idempotency_key, secret)
    if await _operation_replay(
        session,
        key_hash=key_hash,
        order_id=order_id,
        event_type="CANCEL",
        reason=payload.reason,
    ):
        return _detail(order)
    cancellable = {
        OrderStatus.AWAITING_PAYMENT,
        OrderStatus.CONFIRMED,
        OrderStatus.PROCESSING,
        OrderStatus.REFUND_REQUIRED,
    }
    if order.status not in cancellable:
        raise ApiError(409, "order_not_cancellable", "This order can no longer be cancelled.")

    previous = order.status
    payment = _latest_payment(order)
    reservation = order.reservation
    if previous is OrderStatus.AWAITING_PAYMENT:
        if reservation is not None and reservation.status is ReservationStatus.ACTIVE:
            variants = await _locked_variants(
                session, [item.variant_id for item in reservation.items]
            )
            for reservation_item in reservation.items:
                variant = variants[reservation_item.variant_id]
                if variant.reserved_quantity < reservation_item.quantity:
                    raise ApiError(409, "inventory_inconsistent", "The order cannot be reconciled.")
                variant.reserved_quantity -= reservation_item.quantity
            reservation.status = ReservationStatus.RELEASED
            reservation.released_at = datetime.now(UTC)
        if payment.status is not PaymentStatus.SUCCESS:
            payment.status = PaymentStatus.FAILED
            payment.failure_code = "order_cancelled"
    elif previous in {OrderStatus.CONFIRMED, OrderStatus.PROCESSING}:
        if payment.status is not PaymentStatus.SUCCESS:
            raise ApiError(409, "payment_not_successful", "The paid order cannot be reconciled.")
        if reservation is None or reservation.status is not ReservationStatus.CONVERTED:
            raise ApiError(409, "inventory_inconsistent", "The paid order cannot be reconciled.")
        variants = await _locked_variants(session, [item.variant_id for item in order.items])
        for order_item in order.items:
            variant = variants[order_item.variant_id]
            variant.stock_on_hand += order_item.quantity
            session.add(
                InventoryMovement(
                    variant_id=variant.id,
                    movement_type=InventoryMovementType.CANCELLATION_RESTOCK,
                    quantity_delta=order_item.quantity,
                    reason=payload.reason,
                    idempotency_key=f"cancel:{order.id}:{variant.id}",
                    order_id=order.id,
                    reservation_id=reservation.id,
                    actor_user_id=actor_user_id,
                )
            )

    if payment.status is PaymentStatus.SUCCESS:
        refund_now = datetime.now(UTC)
        order.refunds.append(
            Refund(
                id=uuid4(),
                order_id=order.id,
                payment_id=payment.id,
                payment=payment,
                amount_minor=payment.expected_amount_minor,
                currency=payment.currency,
                reason=payload.reason,
                mode=RefundMode.MANUAL,
                status=RefundStatus.PENDING,
                created_by_user_id=actor_user_id,
                created_at=refund_now,
                updated_at=refund_now,
            )
        )

    order.status = OrderStatus.CANCELLED
    order.cancellation_reason = payload.reason
    session.add(
        OrderStatusEvent(
            order=order,
            previous_status=previous,
            new_status=OrderStatus.CANCELLED,
            event_type="CANCEL",
            reason=payload.reason,
            idempotency_key_hash=key_hash,
            actor_user_id=actor_user_id,
        )
    )
    await _commit_operation(session)
    logger.info(
        "order_status_changed",
        extra={
            "order_id": str(order.id),
            "previous_status": previous.value,
            "status": order.status.value,
            "changed_at": datetime.now(UTC).isoformat(),
            "trigger": "CANCEL",
            "refund_required": payment.status is PaymentStatus.SUCCESS,
        },
    )
    return _detail(order)


async def complete_refund(
    session: AsyncSession,
    refund_id: UUID,
    payload: RefundCompletionRequest,
    *,
    actor_user_id: UUID,
    idempotency_key: str,
    secret: str,
) -> AdminOrderDetail:
    refund = await session.scalar(
        # NOTE: no joinedload here — PostgreSQL rejects bare FOR UPDATE over
        # the outer join it produces.
        select(Refund)
        .where(Refund.id == refund_id)
        .with_for_update()
        .options(selectinload(Refund.payment))
    )
    if refund is None:
        raise ApiError(404, "refund_not_found", "The refund could not be found.")
    order = await _locked_order(session, refund.order_id)
    key_hash = hash_token(idempotency_key, secret)
    if refund.status is RefundStatus.SUCCESS:
        if refund.completed_idempotency_key_hash == key_hash:
            return _detail(order)
        raise ApiError(409, "refund_already_completed", "The refund was already completed.")
    if refund.status is not RefundStatus.PENDING:
        raise ApiError(409, "refund_not_pending", "The refund cannot be completed.")

    now = datetime.now(UTC)
    refund.status = RefundStatus.SUCCESS
    refund.manual_reference = payload.manual_reference
    refund.completed_idempotency_key_hash = key_hash
    refund.completed_by_user_id = actor_user_id
    refund.completed_at = now
    refund.payment.status = (
        PaymentStatus.REFUNDED
        if refund.amount_minor == refund.payment.expected_amount_minor
        else PaymentStatus.PARTIALLY_REFUNDED
    )
    await _commit_operation(session)
    logger.info(
        "refund_status_changed",
        extra={
            "order_id": str(order.id),
            "refund_id": str(refund.id),
            "status": refund.status.value,
            "changed_at": now.isoformat(),
            "trigger": "MANUAL_REFUND_RECORDED",
        },
    )
    return _detail(order)
