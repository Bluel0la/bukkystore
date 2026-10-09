from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from bukkystore_api.admin_orders.schemas import (
    AdminOrderListQuery,
    OrderCancellationRequest,
    OrderTransitionAction,
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
from bukkystore_api.catalogue.models import ProductVariant, VariantStatus
from bukkystore_api.commerce.models import (
    InventoryReservation,
    Order,
    OrderItem,
    OrderStatus,
    Payment,
    PaymentStatus,
    Refund,
    RefundMode,
    RefundStatus,
    ReservationItem,
    ReservationStatus,
)
from bukkystore_api.errors import ApiError


class ScalarItems:
    def __init__(self, items: list[object]) -> None:
        self.items = items

    def unique(self) -> ScalarItems:
        return self

    def all(self) -> list[object]:
        return self.items

    def one_or_none(self) -> object | None:
        return self.items[0] if self.items else None


def _order() -> Order:
    now = datetime.now(UTC)
    order = Order(
        id=uuid4(),
        order_number="BS-20260829-ORDER",
        idempotency_key_hash="key-hash",
        request_fingerprint="fingerprint",
        access_token_hash="access-hash",
        customer_full_name="Ada Okafor",
        customer_phone="08012345678",
        customer_email="ada@example.com",
        delivery_area_id=uuid4(),
        delivery_area_name="Lagos Mainland",
        delivery_address="12 Example Street",
        delivery_directions="Beside the bank",
        subtotal_minor=100_000,
        delivery_fee_minor=20_000,
        total_minor=120_000,
        currency="NGN",
        status=OrderStatus.CONFIRMED,
        created_at=now,
        updated_at=now,
    )
    order.items.append(
        OrderItem(
            id=uuid4(),
            product_id=uuid4(),
            variant_id=uuid4(),
            product_name="Brown Dress",
            variant_name="Brown / M",
            sku="DRESS-BRN-M",
            unit_price_minor=100_000,
            quantity=1,
            line_subtotal_minor=100_000,
            created_at=now,
        )
    )
    order.payments.append(
        Payment(
            id=uuid4(),
            provider="fake",
            internal_reference="BKS-ORDER",
            expected_amount_minor=120_000,
            currency="NGN",
            status=PaymentStatus.SUCCESS,
            expires_at=now + timedelta(minutes=15),
            created_at=now,
            updated_at=now,
        )
    )
    return order


async def test_list_admin_orders_maps_latest_payment_and_filters() -> None:
    order = _order()
    session = MagicMock(spec=AsyncSession)
    session.scalars = AsyncMock(return_value=ScalarItems([order]))

    page = await list_admin_orders(
        session,
        AdminOrderListQuery(status=OrderStatus.CONFIRMED, search="Ada", limit=20),
    )

    assert page.items[0].order_number == order.order_number
    assert page.items[0].payment_status is PaymentStatus.SUCCESS
    assert page.items[0].total_minor == 120_000


async def test_get_admin_order_returns_delivery_and_line_items() -> None:
    order = _order()
    session = MagicMock(spec=AsyncSession)
    session.scalars = AsyncMock(return_value=ScalarItems([order]))

    detail = await get_admin_order(session, order.id)

    assert detail.delivery_address == "12 Example Street"
    assert detail.items[0].sku == "DRESS-BRN-M"
    assert detail.items[0].quantity == 1


async def test_get_admin_order_rejects_unknown_id() -> None:
    session = MagicMock(spec=AsyncSession)
    session.scalars = AsyncMock(return_value=ScalarItems([]))

    with pytest.raises(ApiError) as error:
        await get_admin_order(session, uuid4())

    assert error.value.code == "order_not_found"


async def test_transition_advances_paid_order_and_is_idempotent() -> None:
    order = _order()
    session = MagicMock(spec=AsyncSession)
    session.scalars = AsyncMock(return_value=ScalarItems([order]))
    session.scalar = AsyncMock(return_value=None)
    session.commit = AsyncMock()

    detail = await transition_order(
        session,
        order.id,
        OrderTransitionRequest(action=OrderTransitionAction.START_PROCESSING),
        actor_user_id=uuid4(),
        idempotency_key="order-transition-test-0001",
        secret="test-secret-value-with-at-least-32-characters",
    )

    assert detail.status is OrderStatus.PROCESSING
    assert "MARK_OUT_FOR_DELIVERY" in detail.available_actions
    session.commit.assert_awaited_once()


async def test_transition_rejects_skipping_fulfilment_steps() -> None:
    order = _order()
    session = MagicMock(spec=AsyncSession)
    session.scalars = AsyncMock(return_value=ScalarItems([order]))
    session.scalar = AsyncMock(return_value=None)

    with pytest.raises(ApiError) as error:
        await transition_order(
            session,
            order.id,
            OrderTransitionRequest(action=OrderTransitionAction.MARK_COMPLETED),
            actor_user_id=uuid4(),
            idempotency_key="order-transition-test-0002",
            secret="test-secret-value-with-at-least-32-characters",
        )

    assert error.value.code == "invalid_order_transition"


async def test_paid_cancellation_restocks_once_and_creates_pending_refund() -> None:
    order = _order()
    variant_id = order.items[0].variant_id
    variant = ProductVariant(
        id=variant_id,
        product_id=uuid4(),
        sku="DRESS-BRN-M",
        display_name="Brown / M",
        stock_on_hand=4,
        reserved_quantity=0,
        low_stock_threshold=2,
        status=VariantStatus.ACTIVE,
    )
    order.reservation = InventoryReservation(
        id=uuid4(),
        status=ReservationStatus.CONVERTED,
        expires_at=datetime.now(UTC),
        converted_at=datetime.now(UTC),
    )
    session = MagicMock(spec=AsyncSession)
    session.scalars = AsyncMock(side_effect=[ScalarItems([order]), ScalarItems([variant])])
    session.scalar = AsyncMock(return_value=None)
    session.commit = AsyncMock()

    detail = await cancel_order(
        session,
        order.id,
        OrderCancellationRequest(reason="Customer requested a cancellation"),
        actor_user_id=uuid4(),
        idempotency_key="order-cancellation-test-0001",
        secret="test-secret-value-with-at-least-32-characters",
    )

    assert detail.status is OrderStatus.CANCELLED
    assert variant.stock_on_hand == 5
    assert detail.refunds[0].status is RefundStatus.PENDING
    assert detail.refunds[0].amount_minor == order.total_minor
    assert "COMPLETE_REFUND" in detail.available_actions


async def test_unpaid_cancellation_releases_reserved_stock_without_refund() -> None:
    order = _order()
    order.status = OrderStatus.AWAITING_PAYMENT
    order.payments[0].status = PaymentStatus.PENDING
    variant = ProductVariant(
        id=order.items[0].variant_id,
        product_id=uuid4(),
        sku="DRESS-BRN-M",
        display_name="Brown / M",
        stock_on_hand=5,
        reserved_quantity=1,
        low_stock_threshold=2,
        status=VariantStatus.ACTIVE,
    )
    order.reservation = InventoryReservation(
        id=uuid4(), status=ReservationStatus.ACTIVE, expires_at=datetime.now(UTC)
    )
    order.reservation.items.append(ReservationItem(variant_id=variant.id, quantity=1))
    session = MagicMock(spec=AsyncSession)
    session.scalars = AsyncMock(side_effect=[ScalarItems([order]), ScalarItems([variant])])
    session.scalar = AsyncMock(return_value=None)
    session.commit = AsyncMock()

    detail = await cancel_order(
        session,
        order.id,
        OrderCancellationRequest(reason="Duplicate order placed by customer"),
        actor_user_id=uuid4(),
        idempotency_key="order-cancellation-test-0002",
        secret="test-secret-value-with-at-least-32-characters",
    )

    assert detail.status is OrderStatus.CANCELLED
    assert variant.reserved_quantity == 0
    assert order.reservation.status is ReservationStatus.RELEASED
    assert order.payments[0].status is PaymentStatus.FAILED
    assert detail.refunds == []


async def test_manual_refund_completion_updates_payment_once() -> None:
    order = _order()
    order.status = OrderStatus.CANCELLED
    now = datetime.now(UTC)
    refund = Refund(
        id=uuid4(),
        order=order,
        order_id=order.id,
        payment=order.payments[0],
        payment_id=order.payments[0].id,
        amount_minor=order.total_minor,
        currency="NGN",
        reason="Customer requested a cancellation",
        mode=RefundMode.MANUAL,
        status=RefundStatus.PENDING,
        created_by_user_id=uuid4(),
        created_at=now,
        updated_at=now,
    )
    session = MagicMock(spec=AsyncSession)
    session.scalar = AsyncMock(return_value=refund)
    session.scalars = AsyncMock(return_value=ScalarItems([order]))
    session.commit = AsyncMock()

    detail = await complete_refund(
        session,
        refund.id,
        RefundCompletionRequest(manual_reference="OPAY-TRANSFER-123"),
        actor_user_id=uuid4(),
        idempotency_key="refund-completion-test-0001",
        secret="test-secret-value-with-at-least-32-characters",
    )

    assert detail.payment_status is PaymentStatus.REFUNDED
    assert detail.refunds[0].status is RefundStatus.SUCCESS
    assert detail.refunds[0].manual_reference == "OPAY-TRANSFER-123"
