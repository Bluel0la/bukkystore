from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from bukkystore_api.admin_orders.schemas import AdminOrderListQuery
from bukkystore_api.admin_orders.service import get_admin_order, list_admin_orders
from bukkystore_api.commerce.models import (
    Order,
    OrderItem,
    OrderStatus,
    Payment,
    PaymentStatus,
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
